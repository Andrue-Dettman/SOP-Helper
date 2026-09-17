"""Shared fixtures for inventory tests.

These tests need a real PostgreSQL instance (CHECK constraints, timestamptz, etc.
aren't portable to SQLite) via `INVENTORY_TEST_DATABASE_URL`. Until a Postgres
instance is available (G1's `app.database.Database` / C3's `infra/compose.yaml`),
the whole suite skips cleanly rather than failing.

`db_session` mirrors `app.database.Database.read_session` exactly (REPEATABLE READ
transaction, `SET TRANSACTION READ ONLY`) so query functions are exercised under
the same transaction discipline they run under in production.
"""

from __future__ import annotations

import asyncio
import os
import sys

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.inventory.models import Base
from data.inventory.seed import reset_and_seed

if sys.platform == "win32":
    # psycopg3's async mode raises InterfaceError under the default Windows
    # ProactorEventLoop; this affects the real app runtime too, not just tests
    # -- worth flagging to G1, not something to silently paper over elsewhere.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TEST_DATABASE_URL = os.environ.get("INVENTORY_TEST_DATABASE_URL")
# Real demo-database identity check is TBD by G1/C3; empty marker is a no-op guard.
TEST_DB_MARKER = os.environ.get("INVENTORY_TEST_DB_MARKER", "")


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    if not TEST_DATABASE_URL:
        pytest.skip(
            "INVENTORY_TEST_DATABASE_URL not set; requires a local Postgres instance "
            "(see app.database.Database / C3's infra/compose.yaml once available)"
        )
    engine = create_async_engine(TEST_DATABASE_URL, isolation_level="REPEATABLE READ")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(async_engine):
    # Seeding uses a separate, plain synchronous engine/session, matching the real
    # seed/migration credential being distinct from the async runtime session.
    sync_engine = create_engine(TEST_DATABASE_URL)
    sync_session = sessionmaker(bind=sync_engine)()
    try:
        reset_and_seed(sync_session, expected_database_marker=TEST_DB_MARKER)
        sync_session.commit()
    finally:
        sync_session.close()
        sync_engine.dispose()

    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with session_factory() as session:
        async with session.begin():
            await session.execute(text("SET TRANSACTION READ ONLY"))
            yield session


@pytest_asyncio.fixture()
async def db_write_session(db_session, async_engine):
    """A writable session for tests that must prove a DB constraint fires.

    `db_session` is deliberately read-only (it mirrors the production runtime
    role); constraint tests need to attempt a write, so they get their own
    session against the same already-seeded data instead.
    """
    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
