"""Persistent, atomic corpus publication. Writer sessions are never runtime sessions."""

from dataclasses import replace
import asyncio
import json

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from . import schema
from .catalog import (EmbeddingBatch, Generation, MemoryCatalog, PublicationConflict, Snapshot,
                      corpus_revision, ingest, validate_vectors)
from .models import SourceValidationError
from .parser import CHUNKER_VERSION, chunk_document, parse_document


async def active_revision(session):
    return await session.scalar(sa.select(schema.active.c.revision).where(schema.active.c.singleton == 1))


async def archived_document(session, document_id, version):
    row = (await session.execute(sa.select(schema.documents).where(
        schema.documents.c.document_id == document_id, schema.documents.c.version == version))).mappings().first()
    if row is None:
        return None
    document = parse_document(row['source'].encode('utf-8'))
    if document.key != (document_id, version) or document.checksum != row['checksum']:
        raise SourceValidationError('Stored source failed its identity/checksum check')
    return document


async def load_snapshot(session):
    revision = await active_revision(session)
    if revision is None:
        return None
    row = (await session.execute(sa.select(schema.revisions).where(
        schema.revisions.c.revision == revision))).mappings().one()
    if row['chunker_version'] != CHUNKER_VERSION:
        raise SourceValidationError('Stored corpus requires a different chunker version')
    memberships = (await session.execute(sa.select(schema.membership).where(
        schema.membership.c.revision == revision).order_by(
            schema.membership.c.document_id, schema.membership.c.version))).mappings().all()
    documents, current = [], set()
    for member in memberships:
        document = await archived_document(session, member['document_id'], member['version'])
        if document is None:
            raise SourceValidationError('Incomplete stored corpus')
        documents.append(document)
        if member['is_current']:
            current.add(document.key)
    if not documents or not current:
        raise SourceValidationError('Stored corpus has no current documents')
    chunks = tuple(chunk for document in documents for chunk in chunk_document(document))
    persisted_ids = set((await session.execute(sa.select(schema.revision_chunks.c.chunk_id).where(
        schema.revision_chunks.c.revision == revision))).scalars())
    if persisted_ids != {chunk.chunk_id for chunk in chunks}:
        raise SourceValidationError('Stored chunk membership is incomplete')
    generation, vectors = None, ()
    if row['generation_id'] is not None:
        settings = (await session.execute(sa.select(schema.generations).where(
            schema.generations.c.generation_id == row['generation_id']))).mappings().one()
        generation = Generation(**settings)
        indexed = (await session.execute(sa.text(
            'SELECT chunk_id, embedding::text AS value FROM sop_embeddings '
            'WHERE generation_id = :generation_id AND chunk_id = ANY(:ids)'),
            {'generation_id': generation.generation_id, 'ids': [chunk.chunk_id for chunk in chunks]})).mappings()
        by_id = {item['chunk_id']: json.loads(item['value']) for item in indexed}
        if set(by_id) != persisted_ids:
            raise SourceValidationError('Stored embeddings are incomplete')
        vectors = validate_vectors(EmbeddingBatch(generation, [by_id[chunk.chunk_id] for chunk in chunks]),
                                   generation, len(chunks))
    if corpus_revision(tuple(documents), current, generation) != revision:
        raise SourceValidationError('Stored corpus revision does not match its content')
    return Snapshot(revision, tuple(documents), frozenset(current), chunks, generation, vectors)


async def publish_snapshot(session, snapshot, expected_revision):
    """Caller owns a write transaction. Publication is serialized and all-or-nothing."""
    await session.execute(sa.text('SELECT pg_advisory_xact_lock(72026091602)'))
    previous = await active_revision(session)
    if previous == snapshot.revision:
        return False
    if previous != expected_revision:
        raise PublicationConflict('Corpus changed while indexing; retry from current revision')
    for document in snapshot.documents:
        stored = await archived_document(session, *document.key)
        if stored is not None and stored.checksum != document.checksum:
            raise SourceValidationError('Existing document/version content is immutable')
        await session.execute(insert(schema.documents).values(document_id=document.document_id,
            version=document.version, checksum=document.checksum, source=document.source).on_conflict_do_nothing())
        for section in document.sections:
            await session.execute(insert(schema.sections).values(document_id=document.document_id,
                version=document.version, section_id=section.section_id, title=section.title,
                text=section.text).on_conflict_do_nothing())
    for chunk in snapshot.chunks:
        await session.execute(insert(schema.chunks).values(chunk_id=chunk.chunk_id,
            document_id=chunk.document_id, version=chunk.version, section_id=chunk.section_id,
            chunker_version=snapshot.chunker_version).on_conflict_do_nothing())
    if snapshot.generation:
        generation = snapshot.generation
        values = {'generation_id': generation.generation_id, 'provider': generation.provider,
                  'model': generation.model, 'dimension': generation.dimension}
        stored = (await session.execute(sa.select(schema.generations).where(
            schema.generations.c.generation_id == generation.generation_id))).mappings().first()
        if stored is not None and dict(stored) != values:
            raise SourceValidationError('Embedding generation identity is immutable')
        await session.execute(insert(schema.generations).values(**values).on_conflict_do_nothing())
        vectors = validate_vectors(EmbeddingBatch(generation, snapshot.vectors), generation, len(snapshot.chunks))
        for chunk, vector in zip(snapshot.chunks, vectors, strict=True):
            await session.execute(sa.text(
                'INSERT INTO sop_embeddings (generation_id, chunk_id, embedding) '
                'VALUES (:generation, :chunk, CAST(:embedding AS vector)) '
                'ON CONFLICT (generation_id, chunk_id) DO NOTHING'),
                {'generation': generation.generation_id, 'chunk': chunk.chunk_id,
                 'embedding': json.dumps(vector, allow_nan=False)})
    await session.execute(insert(schema.revisions).values(revision=snapshot.revision,
        chunker_version=snapshot.chunker_version,
        generation_id=snapshot.generation.generation_id if snapshot.generation else None).on_conflict_do_nothing())
    for document in snapshot.documents:
        await session.execute(insert(schema.membership).values(revision=snapshot.revision,
            document_id=document.document_id, version=document.version,
            is_current=document.key in snapshot.current).on_conflict_do_nothing())
    for chunk in snapshot.chunks:
        await session.execute(insert(schema.revision_chunks).values(revision=snapshot.revision,
            chunk_id=chunk.chunk_id).on_conflict_do_nothing())
    await session.execute(insert(schema.active).values(singleton=1, revision=snapshot.revision).on_conflict_do_update(
        index_elements=['singleton'], set_={'revision': snapshot.revision}))
    return True


async def ingest_postgres(root, writer_sessions, *, generation=None, provider=None, timeout_s=10.0):
    """Stage embeddings before the writer transaction; no partial active indexes."""
    if (generation is None) != (provider is None):
        raise SourceValidationError('Generation and embedding provider must be supplied together')
    staged = ingest(root, MemoryCatalog())
    revision = corpus_revision(staged.documents, staged.current, generation)
    async with writer_sessions() as session:
        previous = await active_revision(session)
        if previous == revision:
            return revision
    vectors = ()
    if generation:
        texts = [chunk.title + '\n' + chunk.text for chunk in staged.chunks]
        for start in range(0, len(texts), 128):
            inputs = texts[start:start + 128]
            async with asyncio.timeout(timeout_s):
                batch = await provider.embed(inputs, timeout_s)
            actual = Generation(generation.generation_id, batch.provider, batch.model, batch.dimension)
            vectors += validate_vectors(EmbeddingBatch(actual, batch.vectors), generation, len(inputs))
    staged = replace(staged, revision=revision, generation=generation, vectors=vectors)
    async with writer_sessions() as session:
        async with session.begin():
            await publish_snapshot(session, staged, previous)
    return revision
