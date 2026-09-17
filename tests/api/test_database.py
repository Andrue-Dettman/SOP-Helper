from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from app import database


async def test_read_session_sets_read_only_before_any_domain_query(monkeypatch):
    events = []

    class Session:
        @asynccontextmanager
        async def begin(self):
            events.append("begin")
            try:
                yield
            finally:
                events.append("end")

        async def execute(self, sql):
            events.append(str(sql))

    @asynccontextmanager
    async def session():
        yield Session()

    def engine(url, **kwargs):
        assert kwargs["isolation_level"] == "REPEATABLE READ"
        return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

    monkeypatch.setattr(database, "create_async_engine", engine)
    monkeypatch.setattr(database, "async_sessionmaker", lambda *args, **kwargs: session)
    db = database.Database("postgresql+psycopg://fictional")
    async with db.read_session() as connection:
        await connection.execute("domain read")
    assert events == ["begin", "SET TRANSACTION READ ONLY", "domain read", "end"]


async def test_read_session_exits_transaction_on_failure(monkeypatch):
    closed = []

    class Session:
        @asynccontextmanager
        async def begin(self):
            try:
                yield
            finally:
                closed.append(True)

        async def execute(self, sql):
            pass

    @asynccontextmanager
    async def session():
        yield Session()

    monkeypatch.setattr(database, "create_async_engine", lambda *args, **kwargs: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")))
    monkeypatch.setattr(database, "async_sessionmaker", lambda *args, **kwargs: session)
    with pytest.raises(RuntimeError):
        async with database.Database("postgresql+psycopg://fictional").read_session():
            raise RuntimeError("domain failure")
    assert closed == [True]
