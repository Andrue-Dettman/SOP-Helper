"""Shared database bootstrap. Never creates tables, seeds, or migrates at startup."""
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, runtime_url: str):
        self.engine = create_async_engine(runtime_url, isolation_level="REPEATABLE READ", pool_pre_ping=True)
        if self.engine.dialect.name != "postgresql":
            raise ValueError("The demo runtime requires PostgreSQL")
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    @asynccontextmanager
    async def read_session(self):
        async with self.sessions() as session:
            async with session.begin():
                await session.execute(text("SET TRANSACTION READ ONLY"))
                yield session

    async def ready(self):
        async with self.read_session() as session:
            await session.execute(text("SELECT 1"))
        return True

    async def close(self):
        await self.engine.dispose()
