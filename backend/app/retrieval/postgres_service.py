"""Async retrieval implementation for G1's Services protocol methods."""

import asyncio
from dataclasses import replace
import json
import math

import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError

from app.contracts.models import ProcedureSelection, SearchArguments, SourceSection
from app.contracts.services import DependencyFailure

from ..ingestion import schema
from ..ingestion.catalog import EmbeddingBatch, Generation, MemoryCatalog, validate_vectors
from ..ingestion.models import SourceValidationError, source_uri
from ..ingestion.parser import chunk_document
from ..ingestion.postgres import active_revision, archived_document, load_snapshot
from .api_adapter import contract_result
from .ranking import Hit
from .service import ProcedureService, Selection

LEXICAL_SQL = sa.text('''
    WITH source AS (
        SELECT chunk_id, to_tsvector('english', body) AS document
        FROM unnest(CAST(:ids AS text[]), CAST(:bodies AS text[])) AS input(chunk_id, body)
    ), query AS (SELECT plainto_tsquery('english', :query) AS terms)
    SELECT chunk_id, ts_rank_cd(document, terms) AS score
    FROM source CROSS JOIN query WHERE document @@ terms ORDER BY score DESC, chunk_id ASC
''')
VECTOR_SQL = sa.text('''
    WITH source AS (
        SELECT chunk_id, CAST(embedding AS vector) AS embedding
        FROM unnest(CAST(:ids AS text[]), CAST(:vectors AS text[])) AS input(chunk_id, embedding)
    ), scored AS (
        SELECT chunk_id, 1 - (embedding <=> CAST(:query AS vector)) AS score FROM source
    )
    SELECT chunk_id, score FROM scored WHERE score >= :threshold ORDER BY score DESC, chunk_id ASC
''')


def _database_failure(exc):
    if getattr(getattr(exc, 'orig', None), 'sqlstate', None) == '57014':
        raise TimeoutError('Retrieval database deadline expired') from exc
    raise DependencyFailure('retrieval_database_unavailable', retryable=True) from exc


class PostgresRetrievalServices:
    def __init__(self, database, *, mode='lexical', provider=None,
                 minimum_similarity=None, timeout_s=10.0):
        if mode not in ('lexical', 'embedding'):
            raise ValueError('Choose lexical or embedding mode')
        if mode == 'embedding' and (provider is None or type(minimum_similarity) not in (int, float)
                                   or not math.isfinite(minimum_similarity) or not -1 <= minimum_similarity <= 1):
            raise ValueError('Embedding retrieval needs an adapter and explicit acceptance threshold')
        if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 10:
            raise ValueError('Retrieval attempt deadline must be within 10 seconds')
        self.database, self.mode, self.provider = database, mode, provider
        self.minimum_similarity, self.timeout_s = minimum_similarity, timeout_s

    async def _deadline(self, session):
        await session.execute(sa.text("SELECT set_config('statement_timeout', :ms, true)"),
                              {'ms': str(max(1, int(self.timeout_s * 1000)))})

    async def search_procedures(self, query, limit=5, *, selection=None):
        arguments = SearchArguments(query=query, limit=limit)
        selection = ProcedureSelection.model_validate(selection) if selection is not None else None
        try:
            async with asyncio.timeout(self.timeout_s), self.database.read_session() as session:
                await self._deadline(session)
                snapshot = await load_snapshot(session)
                if snapshot is None:
                    raise DependencyFailure('retrieval_corpus_missing')
                if selection and not any(doc.key == (selection.document_id, selection.version)
                                         for doc in snapshot.documents):
                    document = await archived_document(session, selection.document_id, selection.version)
                    if document:
                        snapshot = replace(snapshot, documents=(*snapshot.documents, document),
                                           chunks=(*snapshot.chunks, *chunk_document(document)))
                eligible = [chunk for chunk in snapshot.chunks
                            if (chunk.document_id, chunk.version) in snapshot.current]
                hits, method = (), 'explicit-selection'
                if selection is None and self.mode == 'lexical':
                    rows = await session.execute(LEXICAL_SQL, {'ids': [chunk.chunk_id for chunk in eligible],
                        'bodies': [chunk.title + '\n' + chunk.text for chunk in eligible], 'query': arguments.query})
                    hits = tuple(Hit(chunk_id, float(score)) for chunk_id, score in rows)
                    method = 'postgres-ts-rank-cd-english'
                elif selection is None:
                    if snapshot.generation is None:
                        raise DependencyFailure('retrieval_embeddings_missing')
                    batch = await self.provider.embed([arguments.query], self.timeout_s)
                    generation = snapshot.generation
                    actual = Generation(generation.generation_id, batch.provider, batch.model, batch.dimension)
                    query_vector = validate_vectors(EmbeddingBatch(actual, batch.vectors), generation, 1)[0]
                    vectors = dict(zip((chunk.chunk_id for chunk in snapshot.chunks), snapshot.vectors, strict=True))
                    rows = await session.execute(VECTOR_SQL, {'ids': [chunk.chunk_id for chunk in eligible],
                        'vectors': [json.dumps(vectors[chunk.chunk_id], allow_nan=False) for chunk in eligible],
                        'query': json.dumps(query_vector, allow_nan=False), 'threshold': self.minimum_similarity})
                    hits = tuple(Hit(chunk_id, float(score)) for chunk_id, score in rows)
                    method = 'pgvector-exact-cosine'
                # This memory object holds the already validated, pinned database
                # snapshot. It is not a fallback database or another publication.
                catalog = MemoryCatalog()
                catalog.publish(snapshot, None)

                class Ranked:
                    score_method = method
                    def rank(self, query, chunks):
                        return hits

                context = Selection(selection.document_id, selection.version, selection.section_id) if selection else None
                result = ProcedureService(catalog, mode='lexical', lexical=Ranked()).search_procedures(
                    arguments.query, arguments.limit, selection=context)
                result['retrieval_mode'] = self.mode
                return contract_result(result, snapshot)
        except SQLAlchemyError as exc:
            _database_failure(exc)
        except SourceValidationError as exc:
            raise DependencyFailure('retrieval_invalid_index') from exc

    async def section(self, document_id, version, section_id):
        try:
            async with asyncio.timeout(self.timeout_s), self.database.read_session() as session:
                await self._deadline(session)
                document = await archived_document(session, document_id, version)
                section = next((s for s in document.sections if s.section_id == section_id), None) if document else None
                if section is None:
                    return None
                revision = await active_revision(session)
                current = await session.scalar(sa.select(schema.membership.c.is_current).where(
                    schema.membership.c.revision == revision, schema.membership.c.document_id == document_id,
                    schema.membership.c.version == version))
                return SourceSection(document_id=document_id, version=version, section_id=section_id,
                    title=section.title, text=section.text, source_uri=source_uri(document_id, version, section_id),
                    is_current=current is True)
        except SQLAlchemyError as exc:
            _database_failure(exc)
        except SourceValidationError as exc:
            raise DependencyFailure('retrieval_invalid_index') from exc

    async def readiness(self):
        try:
            async with asyncio.timeout(self.timeout_s), self.database.read_session() as session:
                await self._deadline(session)
                return True, await load_snapshot(session) is not None
        except (SQLAlchemyError, SourceValidationError, TimeoutError):
            return False, False
