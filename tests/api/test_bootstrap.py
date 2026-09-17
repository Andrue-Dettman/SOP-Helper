import sys
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

from app.api import bootstrap
from app.contracts.models import ProcedureSelection
from conftest import FakeServices


async def test_composition_preserves_domain_results_and_selected_context(services):
    async def database_ready():
        return True
    services.database_ready = database_ready
    composed = bootstrap.ComposedServices(services, services)
    assert await composed.lookup_stock("P1") is services.stock
    assert (await composed.assemblies("kit", 1))[0].assembly_id == "A1"
    assert (await composed.check_build_readiness("A1", 20)).components[0].shortage == 35
    selected = ProcedureSelection(document_id="receiving", version="1", section_id="inspect")
    assert await composed.search_procedures("explain", 5, selection=selected) is services.search
    assert services.calls[-1][-1] is selected
    assert (await composed.section("receiving", "1", "inspect")).version == "1"
    assert await composed.readiness() == (True, True)


@pytest.mark.parametrize("inventory_ready,retrieval_ready,expected", [
    (False, (True, True), (False, True)),
    (True, (True, False), (True, False)),
    (True, (False, False), (False, False)),
])
async def test_readiness_requires_both_domain_checks(inventory_ready, retrieval_ready, expected):
    class Inventory:
        async def database_ready(self):
            return inventory_ready
    class Retrieval:
        async def readiness(self):
            return retrieval_ready
    assert await bootstrap.ComposedServices(Inventory(), Retrieval()).readiness() == expected


def test_runtime_factory_requires_explicit_runtime_database(monkeypatch):
    monkeypatch.delenv("RUNTIME_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="RUNTIME_DATABASE_URL is required"):
        bootstrap.create_runtime_app()


@pytest.mark.parametrize("threshold", [None, "not-a-number", "NaN", "Infinity", "1.1"])
def test_embedding_threshold_is_explicit_and_bounded(monkeypatch, threshold):
    monkeypatch.setenv("RUNTIME_DATABASE_URL", "postgresql+psycopg://fictional")
    monkeypatch.setenv("RETRIEVAL_MODE", "embedding")
    monkeypatch.delenv("RETRIEVAL_MINIMUM_SIMILARITY", raising=False)
    if threshold is not None:
        monkeypatch.setenv("RETRIEVAL_MINIMUM_SIMILARITY", threshold)
    with pytest.raises(RuntimeError, match="RETRIEVAL_MINIMUM_SIMILARITY"):
        bootstrap.create_runtime_app()


def test_runtime_factory_wires_services_and_closes_database(monkeypatch):
    created = []
    class Database:
        def __init__(self, url):
            self.closed = False
            created.append(self)
        async def close(self):
            self.closed = True
    class Inventory(FakeServices):
        def __init__(self, database):
            super().__init__()
            self.database = database
        async def database_ready(self):
            return True
    class Retrieval(FakeServices):
        def __init__(self, database, **settings):
            super().__init__()
            self.database, self.settings = database, settings
    inventory_module = ModuleType("app.inventory.service")
    inventory_module.InventoryService = Inventory
    retrieval_module = ModuleType("app.retrieval.postgres_service")
    retrieval_module.PostgresRetrievalServices = Retrieval
    monkeypatch.setitem(sys.modules, "app.inventory.service", inventory_module)
    monkeypatch.setitem(sys.modules, "app.retrieval.postgres_service", retrieval_module)
    monkeypatch.setattr(bootstrap, "Database", Database)
    monkeypatch.setenv("RUNTIME_DATABASE_URL", "postgresql+psycopg://fictional")
    monkeypatch.setenv("RETRIEVAL_MODE", "lexical")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_CHAT_MODEL", raising=False)
    app = bootstrap.create_runtime_app()
    assert app.state.services.inventory.database is app.state.services.retrieval.database
    with TestClient(app) as client:
        assert client.get("/api/assemblies?query=kit").json()["items"][0]["assembly_id"] == "A1"
        readiness = client.get("/api/ready").json()
        assert readiness["database"] == "ready" and readiness["corpus"] == "ready"
        assert readiness["provider"] == "missing" and readiness["status"] == "not_ready"
    assert created[0].closed
