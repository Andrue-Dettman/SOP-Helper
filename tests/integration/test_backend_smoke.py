"""Exercises the real, integrated backend container over HTTP.

Requires `scripts/integration-test.sh` (migrates + seeds + starts db and
backend) or an equivalent manual setup; see tests/integration/README.md and
docs/operations.md. No provider credentials are required: C1's inventory
and G2's retrieval are real and seeded, so database/corpus checks and
non-LLM endpoints (assemblies, source sections) exercise real data. Only
the provider (OPENAI_API_KEY) is intentionally left unconfigured here, so
/api/chat still honestly reports temporarily_unavailable rather than
fabricating a model answer, per docs/CONTRACTS.md.
"""
import os

import httpx

BASE_URL = f"http://localhost:{os.environ.get('API_PORT', '8100')}"


def test_health_is_ok():
    response = httpx.get(f"{BASE_URL}/api/health", timeout=10)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_real_database_and_corpus_but_missing_provider():
    response = httpx.get(f"{BASE_URL}/api/ready", timeout=10)
    assert response.status_code == 503
    body = response.json()
    # Real, not fabricated: C1's inventory and G2's corpus are migrated and
    # seeded by scripts/migrate-and-seed.sh before this test runs. Only the
    # provider is deliberately left unconfigured in offline CI.
    assert body["database"] == "ready"
    assert body["corpus"] == "ready"
    assert body["provider"] == "missing"
    assert body["status"] == "not_ready"


def test_assemblies_returns_real_seeded_catalog():
    response = httpx.get(f"{BASE_URL}/api/assemblies", params={"query": "widget", "limit": 5}, timeout=10)
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(item["assembly_id"] == "ASM-0001" for item in items)


def test_sop_section_returns_real_ingested_text():
    response = httpx.get(
        f"{BASE_URL}/api/sops/receiving-delivery/sections/inspect-and-count",
        params={"version": "2"},
        timeout=10,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_current"] is True
    assert "Inspect the packages before opening them" in body["text"]


def test_sop_missing_version_404s_without_substituting_current_text():
    response = httpx.get(
        f"{BASE_URL}/api/sops/receiving-delivery/sections/inspect-and-count",
        params={"version": "99"},
        timeout=10,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "source_not_found"


def test_chat_reports_temporarily_unavailable_without_fabricating_an_answer():
    response = httpx.post(
        f"{BASE_URL}/api/chat",
        json={"message": "How do I receive a delivery?"},
        timeout=10,
    )
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "temporarily_unavailable"
    assert body["error"]["code"] == "provider_not_configured"
    assert body["data_mode"] == "synthetic"
    assert body["citations"] == []
    assert body["procedure_result"] is None
    assert body["inventory_result"] is None


def test_invalid_chat_request_is_rejected_before_any_dependency_call():
    response = httpx.post(f"{BASE_URL}/api/chat", json={"message": ""}, timeout=10)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
