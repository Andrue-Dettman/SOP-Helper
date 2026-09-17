"""Exercises the real backend container over HTTP.

Requires `docker compose -f infra/compose.yaml up -d --build db backend`
(or `scripts/integration-test.sh`) already running; see
tests/integration/README.md and docs/operations.md. No provider
credentials or seed data are required: this only asserts the honest
not-configured/unavailable behavior that G1's backend reports today, per
docs/CONTRACTS.md's explicit-dependency-state requirement. It needs
extending, not replacing, once C1/G2's real services are wired in (see
tests/integration/README.md for the planned "state=ok" scenarios).
"""
import os

import httpx

BASE_URL = f"http://localhost:{os.environ.get('API_PORT', '8100')}"


def test_health_is_ok():
    response = httpx.get(f"{BASE_URL}/api/health", timeout=10)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_unavailable_dependencies_honestly():
    response = httpx.get(f"{BASE_URL}/api/ready", timeout=10)
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    # Explicit, not a fabricated success: C1/G2's real inventory/retrieval
    # wiring has not been merged into this backend yet.
    assert body["database"] == "unavailable"


def test_chat_reports_temporarily_unavailable_without_fabricating_an_answer():
    response = httpx.post(
        f"{BASE_URL}/api/chat",
        json={"message": "How do I receive a delivery?"},
        timeout=10,
    )
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "temporarily_unavailable"
    assert body["data_mode"] == "synthetic"
    assert body["citations"] == []
    assert body["procedure_result"] is None
    assert body["inventory_result"] is None


def test_invalid_chat_request_is_rejected_before_any_dependency_call():
    response = httpx.post(f"{BASE_URL}/api/chat", json={"message": ""}, timeout=10)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
