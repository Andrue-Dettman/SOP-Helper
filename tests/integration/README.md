# Integration tests

## What exists today: `test_backend_smoke.py`

`main` now merges G1 (API/bootstrap), C1 (inventory), G2 (retrieval),
G3 (evaluation), C2 (frontend), and C3 (this delivery scaffolding).
`backend/app/api/bootstrap.py:create_runtime_app` composes C1's
`InventoryService` and G2's `PostgresRetrievalServices` into the real API.
`scripts/migrate-and-seed.sh` runs Alembic migrations, G2's SOP corpus
ingestion, and C1's inventory seed against a fresh `db` container;
`scripts/integration-test.sh` does that, starts `backend` in integrated
mode, and runs this suite against it. All 7 tests pass locally against
real seeded data with zero provider credentials:

- `/api/health`, `/api/ready` (`database`/`corpus` report real `ready`;
  `provider` honestly reports `missing` since no `OPENAI_API_KEY` is
  configured in offline CI — `status` stays `not_ready` for that reason
  alone).
- `/api/assemblies?query=widget` returns the real seeded `ASM-0001`
  ("Widget Kit").
- `/api/sops/receiving-delivery/sections/inspect-and-count?version=2`
  returns the real ingested Markdown text; `version=99` 404s without
  substituting current text.
- `/api/chat` still honestly reports `temporarily_unavailable` /
  `provider_not_configured` (no fabricated answer) since the LLM
  provider itself isn't configured — this is the one piece that
  genuinely needs `OPENAI_API_KEY` and belongs in `live-smoke`, not here.
- Invalid `/api/chat` requests are rejected with `422` before any
  dependency call.

## What this suite still needs

Per `docs/CONTRACTS.md` and PLAN.md's "Required correctness checks":

- A real `/api/chat` round trip needs `OPENAI_API_KEY` (live-smoke only,
  never offline CI) to exercise the three primary workflows end-to-end:
  procedure lookup with citations, passage explanation, and
  build-readiness calculation, including combined questions where one
  part succeeds and another is incomplete.
- Citation shape: `answer_citation_ids` and `procedure_result` step
  `citation_ids` resolve to real `citations` entries; unknown citation
  IDs never become valid links. (Testable once a chat round trip works.)
- Inventory arithmetic scenarios beyond the catalog check here:
  sufficient stock, exact stock, shortages, missing rows, zero stock,
  invalid quantity, empty BOM, duplicate components, ambiguous aliases —
  `tests/inventory/` covers these at the unit level against
  `INVENTORY_TEST_DATABASE_URL`; consider a `check_build_readiness`
  integration case here too once a non-chat route exists to call it
  directly, or via a chat round trip.
- A full browser workflow (Playwright) against the real frontend and
  backend, not just mocked UI fixtures, per C2's acceptance criteria.
  `frontend/` isn't wired into `infra/compose.yaml` yet (see
  docs/operations.md).
- Read-only runtime DB credentials: `backend/app/inventory/db_roles.sql`
  defines `warehouse_runtime_ro`/`warehouse_seed_rw` but nothing creates
  those roles or points `RUNTIME_DATABASE_URL` at the read-only one yet;
  today's `backend` service uses the same admin-ish `warehouse` user for
  everything. Flagged in the SQL file itself as a G1/C3 follow-up.

## Acceptance gate

Per the C3 delivery report (`docs/agent-reports/C3-delivery.md`):
offline CI is green with zero provider credentials present, and this
suite asserts `status`/data shape against the real seeded stack — no
fixture substitution.

## Status

Implemented and passing: `test_backend_smoke.py` (7 tests) against the
real integrated backend with real seeded inventory and corpus data.
Remaining gaps are the live-chat round trip (needs credentials, belongs
in `live-smoke.yml`), the frontend's browser workflow, and DB role
separation — all listed above, not silently dropped.
