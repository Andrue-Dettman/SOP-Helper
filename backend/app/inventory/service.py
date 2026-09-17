"""Adapter exposing C1's inventory queries as the inventory-owned slice of
`app.contracts.services.Services` (`assemblies`, `lookup_stock`,
`check_build_readiness`, plus `database_ready` for the composed `readiness()`).

G2's retrieval methods and the final composed `Services` implementation belong to
G1/the coordinator; this class only covers what C1 owns.
"""

from __future__ import annotations

from app.contracts.models import Assembly, BuildResult, StockResult
from app.contracts.services import DependencyFailure
from app.database import Database

from . import queries


class InventoryService:
    def __init__(self, database: Database):
        self._database = database

    async def assemblies(self, query: str, limit: int) -> list[Assembly]:
        try:
            async with self._database.read_session() as session:
                return await queries.assemblies(session, query, limit)
        except DependencyFailure:
            raise
        except Exception as exc:
            raise DependencyFailure("inventory_unavailable", retryable=True) from exc

    async def lookup_stock(self, part_query: str) -> StockResult:
        try:
            async with self._database.read_session() as session:
                return await queries.lookup_stock(session, part_query)
        except DependencyFailure:
            raise
        except Exception as exc:
            raise DependencyFailure("inventory_unavailable", retryable=True) from exc

    async def check_build_readiness(self, assembly_id: str, quantity: int) -> BuildResult:
        try:
            async with self._database.read_session() as session:
                return await queries.check_build_readiness(session, assembly_id, quantity)
        except DependencyFailure:
            raise
        except Exception as exc:
            raise DependencyFailure("inventory_unavailable", retryable=True) from exc

    async def database_ready(self) -> bool:
        try:
            return await self._database.ready()
        except Exception:
            return False
