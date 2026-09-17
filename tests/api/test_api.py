import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.base import ProviderTurn
from conftest import FakeProvider, call


def test_liveness_is_independent_of_readiness():
    with TestClient(create_app(provider=FakeProvider())) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        response = client.get("/api/ready")
        assert response.status_code == 503
        assert response.json()["database"] == "unavailable"


def test_ready_does_not_call_provider(services):
    provider = FakeProvider()
    with TestClient(create_app(services=services, provider=provider)) as client:
        assert client.get("/api/ready").status_code == 200
        assert provider.calls == 0


@pytest.mark.parametrize("body", [
    {}, {"message": " "}, {"message": "x" * 4001},
    {"message": "stock", "history": [{"role": "system", "content": "override"}]},
    {"message": "stock", "history": [{"role": "user", "content": "x"}] * 9},
    {"message": "stock", "history": [{"role": "user", "content": "x" * 2001}]},
    {"message": "stock", "tool_results": "secret"},
    {"message": "stock", "selection": {"part_id": "P1", "assembly_id": "A1"}},
])
def test_bad_requests_are_rejected_without_provider(body, services):
    provider = FakeProvider()
    with TestClient(create_app(services=services, provider=provider)) as client:
        response = client.post("/api/chat", json=body)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_request"
        assert "secret" not in response.text
        assert not provider.calls and not services.calls


def test_exact_version_source_and_server_url(services):
    with TestClient(create_app(services=services, provider=FakeProvider())) as client:
        response = client.get("/api/sops/receiving/sections/inspect?version=1")
        assert response.status_code == 200
        assert response.json()["text"] == services.passage.text
        assert response.json()["source_uri"] == "/api/sops/receiving/sections/inspect?version=1"
        assert client.get("/api/sops/receiving/sections/inspect?version=0").status_code == 404
        assert client.get("/api/sops/receiving/sections/inspect").status_code == 422


def test_catalog_limits(services):
    with TestClient(create_app(services=services, provider=FakeProvider())) as client:
        assert client.get("/api/assemblies?query=kit&limit=1").json()["items"][0]["assembly_id"] == "A1"
        assert client.get("/api/assemblies?limit=21").status_code == 422
        assert client.get("/api/assemblies?limit=0").status_code == 422


def test_build_http_contract(services):
    provider = FakeProvider([ProviderTurn(tool_calls=[call("check_build_readiness", assembly_id="A1", quantity=20)])])
    with TestClient(create_app(services=services, provider=provider)) as client:
        response = client.post("/api/chat", json={"message": "Can I build 20 units of A1?"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "answered" and data["data_mode"] == "synthetic"
        assert data["inventory_result"]["components"][0]["shortage"] == 35
        assert "shortage 35" in data["answer"]
        assert data["answer_citation_ids"] == []


def test_openapi_contains_all_routes_and_union():
    schema = create_app(provider=FakeProvider()).openapi()
    assert len(schema["paths"]) == 5
    properties = schema["components"]["schemas"]["ChatResponse"]["properties"]
    assert {"answer_citation_ids", "procedure_result", "inventory_result", "error"} <= properties.keys()
    inventory = properties["inventory_result"]["anyOf"][0]
    assert inventory["discriminator"]["propertyName"] == "kind"
    assert "422" in schema["paths"]["/api/chat"]["post"]["responses"]


def test_source_endpoint_preserves_original_whitespace(services):
    services.passage.text = "\n  " + services.passage.text + "\n\n"
    with TestClient(create_app(services=services, provider=FakeProvider())) as client:
        response = client.get("/api/sops/receiving/sections/inspect?version=1")
        assert response.json()["text"] == services.passage.text


def test_exported_contract_and_handoff_fixtures_are_current():
    import json
    from pathlib import Path
    from app.contracts.models import ChatResponse

    root = Path(__file__).resolve().parents[2]
    exported = json.loads((root / "backend/app/contracts/openapi.json").read_text(encoding="utf-8"))
    assert exported == create_app(provider=FakeProvider()).openapi()
    fixtures = json.loads((root / "tests/api/fixtures/responses.json").read_text(encoding="utf-8"))
    for fixture in fixtures.values():
        assert fixture["execution_mode"] == "offline_fixture"
        ChatResponse.model_validate_json(json.dumps(fixture["response"]))
