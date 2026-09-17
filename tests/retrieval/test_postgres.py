"""Opt-in real database checks; only the explicitly named isolated G2 test DB."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
import importlib.util
import json
import os
import selectors
import sys
from pathlib import Path

import pytest

sa = pytest.importorskip('sqlalchemy')
pytest.importorskip('app.database', reason='G1 database baseline is required')

from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Database
from app.contracts.models import ProcedureSelection
from app.contracts.services import DependencyFailure
from app.ingestion import schema
from app.ingestion.catalog import Generation, MemoryCatalog, PublicationConflict, ingest
from app.ingestion.models import SourceValidationError
from app.ingestion.postgres import active_revision, ingest_postgres, load_snapshot, publish_snapshot
from app.providers.base import EmbeddingBatch
from app.retrieval.postgres_service import PostgresRetrievalServices

URL = os.environ.get('WAREHOUSE_G2_TEST_DATABASE_URL')
pytestmark = pytest.mark.skipif(not URL, reason='No isolated G2 PostgreSQL test URL configured')
GENERATION = Generation('offline-database-fixture-v1', 'offline-fixture', 'fixture-vectors', 2)


def run(coroutine):
    if sys.platform == 'win32':
        return asyncio.run(coroutine, loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
    return asyncio.run(coroutine)


class Provider:
    """Fixed vectors test database transport; they do not evaluate a live model."""
    async def embed(self, texts, timeout_s):
        return EmbeddingBatch(provider=GENERATION.provider, model=GENERATION.model, dimension=2,
            vectors=[[1.0, 0.0] if 'delivery' in text.lower() else [0.0, 1.0] for text in texts])


@asynccontextmanager
async def isolated_database():
    url = make_url(URL)
    assert (url.host, url.port, url.database, url.username) == (
        '127.0.0.1', 5502, 'warehouse_g2_test', 'warehouse_g2_test'), 'Refusing non-G2 test database'
    writer = create_async_engine(URL)
    runtime = Database(URL)
    try:
        async with writer.begin() as connection:
            await connection.run_sync(schema.downgrade)
            await connection.run_sync(schema.upgrade)
        yield async_sessionmaker(writer, expire_on_commit=False), runtime
    finally:
        await runtime.close()
        await writer.dispose()


def test_persistent_lexical_lookup_and_read_only_runtime(corpus):
    async def scenario():
        async with isolated_database() as (sessions, database):
            revision = await ingest_postgres(corpus, sessions)
            assert await ingest_postgres(corpus, sessions) == revision
            service = PostgresRetrievalServices(database)
            assert await service.readiness() == (True, True)
            result = await service.search_procedures('receive delivery', 1, selection=None)
            assert result.status == 'ok'
            assert result.corpus_revision == revision
            assert {p.document_id for p in result.passages} == {'receiving-delivery'}
            assert sum(len(p.steps) for p in result.passages) == 4
            assert sum(len(p.warnings) for p in result.passages) == 1
            assert (await service.section('receiving-delivery', '1', 'inspect-and-count')).is_current is False
            assert await service.section('receiving-delivery', 'missing', 'inspect-and-count') is None
            assert (await service.search_procedures('quantum aardvark', 5, selection=None)).status == 'no_evidence'
            # A new connection/service instance must read persisted source data.
            await database.close()
            assert (await PostgresRetrievalServices(database).section('receiving-delivery', '2', 'terms')).is_current
            with pytest.raises(DBAPIError):
                async with database.read_session() as session:
                    await session.execute(sa.text("DELETE FROM sop_active_revision"))
    run(scenario())


def test_real_pgvector_generation_validation(corpus):
    async def scenario():
        async with isolated_database() as (sessions, database):
            revision = await ingest_postgres(corpus, sessions, generation=GENERATION, provider=Provider())
            service = PostgresRetrievalServices(database, mode='embedding', provider=Provider(), minimum_similarity=0.9)
            result = await service.search_procedures('delivery', 1, selection=None)
            assert result.status == 'ok' and result.corpus_revision == revision
            assert all(p.score_method == 'pgvector-exact-cosine' for p in result.passages)
            assert all(p.is_current for p in result.passages)

            class WrongModel(Provider):
                async def embed(self, texts, timeout_s):
                    return (await super().embed(texts, timeout_s)).model_copy(update={'model': 'wrong-model'})

            bad = PostgresRetrievalServices(database, mode='embedding', provider=WrongModel(), minimum_similarity=0.9)
            with pytest.raises(DependencyFailure, match='invalid_index'):
                await bad.search_procedures('delivery', 1, selection=None)
            async with sessions() as session:
                persisted = await load_snapshot(session)
                assert persisted.generation == GENERATION
                assert len(persisted.vectors) == 27
    run(scenario())


def test_failed_indexing_and_immutable_source_keep_active_revision(corpus):
    async def scenario():
        async with isolated_database() as (sessions, database):
            original = await ingest_postgres(corpus, sessions)

            class Failed(Provider):
                async def embed(self, texts, timeout_s):
                    raise TimeoutError('injected failure')

            with pytest.raises(TimeoutError):
                await ingest_postgres(corpus, sessions, generation=GENERATION, provider=Failed())
            file = corpus / 'receiving-delivery/v2.md'
            file.write_bytes(file.read_bytes().replace(b'Count each item', b'Count nothing'))
            with pytest.raises(SourceValidationError, match='immutable'):
                await ingest_postgres(corpus, sessions)
            async with sessions() as session:
                assert await active_revision(session) == original
            assert 'Count each item' in (await PostgresRetrievalServices(database).section(
                'receiving-delivery', '2', 'inspect-and-count')).text
    run(scenario())


def test_database_conflicts_and_historical_selection(corpus):
    async def scenario():
        async with isolated_database() as (sessions, database):
            manifest_path = corpus / 'manifest.json'
            manifest = json.loads(manifest_path.read_text())
            source = (corpus / 'receiving-delivery/v1.md').read_bytes()
            (corpus / 'conflict.md').write_bytes(source.replace(b'"document_id": "receiving-delivery"',
                b'"document_id": "receiving-conflict"'))
            manifest['documents'].append({'path': 'conflict.md', 'current': True})
            manifest_path.write_text(json.dumps(manifest))
            await ingest_postgres(corpus, sessions)
            service = PostgresRetrievalServices(database)
            result = await service.search_procedures('receive delivery', 1, selection=None)
            assert result.status == 'conflict' and not result.passages
            historical = await service.search_procedures('explain', 1, selection=ProcedureSelection(
                document_id='receiving-delivery', version='1', section_id='terms'))
            assert historical.status == 'ok'
            assert all(not p.is_current for p in historical.passages)
    run(scenario())


def test_stale_database_publication_is_rejected(corpus):
    async def scenario():
        async with isolated_database() as (sessions, database):
            original = await ingest_postgres(corpus, sessions)
            staged = ingest(corpus, MemoryCatalog())
            changed = await ingest_postgres(corpus, sessions, generation=GENERATION, provider=Provider())
            assert changed != original
            with pytest.raises(PublicationConflict):
                async with sessions() as session, session.begin():
                    await publish_snapshot(session, staged, None)
            async with sessions() as session:
                assert await active_revision(session) == changed
    run(scenario())


def test_schema_body_after_actual_c1_inventory_revision(corpus):
    migration_path = os.environ.get('WAREHOUSE_C1_MIGRATION')
    if not migration_path:
        pytest.skip('C1 migration path not configured')
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    def apply_inventory(connection):
        spec = importlib.util.spec_from_file_location('g2_test_c1_revision', migration_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.revision == 'c1_0001_inventory_schema'
        if not sa.inspect(connection).has_table('parts'):
            with Operations.context(MigrationContext.configure(connection)):
                module.upgrade()
        schema.downgrade(connection)
        schema.upgrade(connection)
        tables = set(sa.inspect(connection).get_table_names())
        assert {'parts', 'bom_lines', 'inventory_snapshot', 'sop_documents', 'sop_active_revision'} <= tables

    async def scenario():
        async with isolated_database() as (sessions, database):
            async with sessions() as session, session.begin():
                connection = await session.connection()
                await connection.run_sync(apply_inventory)
            await ingest_postgres(corpus, sessions)
            assert await PostgresRetrievalServices(database).readiness() == (True, True)
    run(scenario())
