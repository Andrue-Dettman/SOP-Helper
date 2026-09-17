"""Explicit database-backed factory for the coordinator's integrated checkout.

After C1/G2 are integrated, launch with:
    uvicorn app.api.bootstrap:create_runtime_app --factory --app-dir backend

Requires RUNTIME_DATABASE_URL (read-only runtime credentials). The normal
app.main:app remains a standalone unconfigured API; this factory never seeds,
migrates, provisions, or falls back to an in-memory catalog.
"""
from contextlib import asynccontextmanager
import os

from app.contracts.models import ProcedureSelection
from app.database import Database
from app.main import create_app
from app.providers.openai import OpenAIEmbeddingProvider


class ComposedServices:
    def __init__(self, inventory, retrieval):
        self.inventory, self.retrieval = inventory, retrieval

    async def assemblies(self, query: str, limit: int):
        return await self.inventory.assemblies(query, limit)

    async def lookup_stock(self, part_query: str):
        return await self.inventory.lookup_stock(part_query)

    async def check_build_readiness(self, assembly_id: str, quantity: int):
        return await self.inventory.check_build_readiness(assembly_id, quantity)

    async def search_procedures(self, query: str, limit: int, *, selection: ProcedureSelection | None):
        return await self.retrieval.search_procedures(query, limit, selection=selection)

    async def section(self, document_id: str, version: str, section_id: str):
        return await self.retrieval.section(document_id, version, section_id)

    async def readiness(self):
        database = await self.inventory.database_ready()
        retrieval_database, corpus = await self.retrieval.readiness()
        return database and retrieval_database, corpus


def create_runtime_app():
    runtime_url = os.environ.get("RUNTIME_DATABASE_URL", "")
    if not runtime_url:
        raise RuntimeError("RUNTIME_DATABASE_URL is required for the integrated runtime")
    mode = os.environ.get("RETRIEVAL_MODE", "lexical")
    if mode not in {"lexical", "embedding"}:
        raise RuntimeError("RETRIEVAL_MODE must be lexical or embedding")
    embedding, threshold = None, None
    if mode == "embedding":
        model = os.environ.get("OPENAI_EMBEDDING_MODEL", "")
        key = os.environ.get("OPENAI_API_KEY", "")
        try:
            threshold = float(os.environ["RETRIEVAL_MINIMUM_SIMILARITY"])
            if not -1 <= threshold <= 1:
                raise ValueError()
        except (KeyError, ValueError):
            raise RuntimeError("Embedding retrieval requires RETRIEVAL_MINIMUM_SIMILARITY between -1 and 1") from None
        if not model or not key:
            raise RuntimeError("Embedding retrieval requires OPENAI_EMBEDDING_MODEL and OPENAI_API_KEY")
        embedding = OpenAIEmbeddingProvider(key, model)
    # Import only in the integrated factory. G1's standalone app and offline tests
    # work before sibling modules have been merged by the coordinator.
    try:
        from app.inventory.service import InventoryService
        from app.retrieval.postgres_service import PostgresRetrievalServices
    except ImportError:
        raise RuntimeError("The integrated runtime requires the C1 inventory and G2 retrieval modules") from None
    try:
        database = Database(runtime_url)
    except Exception:
        raise RuntimeError("RUNTIME_DATABASE_URL must identify the runtime PostgreSQL database") from None
    services = ComposedServices(InventoryService(database), PostgresRetrievalServices(
        database, mode=mode, provider=embedding, minimum_similarity=threshold))

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            await database.close()

    return create_app(services=services, lifespan=lifespan)
