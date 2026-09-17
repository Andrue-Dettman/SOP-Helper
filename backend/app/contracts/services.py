"""Domain implementations are supplied by G2/C1; defaults never substitute fixtures."""
from typing import Protocol

from app.contracts.models import Assembly, BuildResult, ProcedureSelection, SearchResult, SourceSection, StockResult


class DependencyFailure(Exception):
    def __init__(self, code="dependency_unavailable", *, retryable=False):
        self.code = code
        self.retryable = retryable
        super().__init__(code)


class Services(Protocol):
    async def search_procedures(self, query: str, limit: int, *, selection: ProcedureSelection | None) -> SearchResult: ...
    async def section(self, document_id: str, version: str, section_id: str) -> SourceSection | None: ...
    async def assemblies(self, query: str, limit: int) -> list[Assembly]: ...
    async def lookup_stock(self, part_query: str) -> StockResult: ...
    async def check_build_readiness(self, assembly_id: str, quantity: int) -> BuildResult: ...
    async def readiness(self) -> tuple[bool, bool]: ...


class UnavailableServices:
    async def search_procedures(self, query, limit, *, selection=None):
        raise DependencyFailure("retrieval_not_configured")

    async def section(self, document_id, version, section_id):
        raise DependencyFailure("retrieval_not_configured")

    async def assemblies(self, query, limit):
        raise DependencyFailure("inventory_not_configured")

    async def lookup_stock(self, part_query):
        raise DependencyFailure("inventory_not_configured")

    async def check_build_readiness(self, assembly_id, quantity):
        raise DependencyFailure("inventory_not_configured")

    async def readiness(self):
        return False, False
