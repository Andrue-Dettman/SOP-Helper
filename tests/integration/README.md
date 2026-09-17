# Integration tests

## What exists today: `test_backend_smoke.py`

G1 (`agent/g1-api`) has landed a real FastAPI backend
(`backend/app/main.py`) that runs standalone — `create_app()` defaults to
`UnavailableServices()` and an unconfigured provider — and honestly
reports `not_ready`/`temporarily_unavailable` rather than fabricating a
response. `test_backend_smoke.py` exercises that real, current behavior
end-to-end over HTTP: `/api/health`, `/api/ready`, a rejected invalid
`/api/chat` request, and a valid one that correctly reports
`temporarily_unavailable` with no invented answer/citations. This was
verified locally by building `infra/Dockerfile.backend` against G1's
actual code and running the suite against the live container (all 4
tests pass) before being committed here; `scripts/integration-test.sh`
reproduces that same run and is wired into `.github/workflows/offline.yml`.

`backend/` is not part of this branch yet — only `infra/`, `scripts/`,
and `tests/integration/` are C3's to commit — so
`scripts/integration-test.sh` skips cleanly (exit 0) until the
coordinator merges `agent/g1-api` in. It stopped being a no-op the
moment real backend code existed to test; it isn't gated on a phase
change.

## What this suite still needs once C1/G2/C2 land

Per `docs/CONTRACTS.md` and PLAN.md's "Required correctness checks", using
mocked provider transport (never live credentials):

- `POST /api/chat` end-to-end for the three primary workflows: procedure
  lookup with citations, passage explanation preserving mandatory steps,
  and build-readiness calculation. (G2's retrieval and C1's inventory
  exist on their own branches now but aren't merged into the backend
  G1 built, so these still return `temporarily_unavailable` today.)
- `status` values (`answered | needs_clarification | insufficient_evidence
  | temporarily_unavailable`) match the scenario, including combined
  questions where one part succeeds and another is incomplete.
- Citation shape: `answer_citation_ids` and `procedure_result` step
  `citation_ids` resolve to real `citations` entries; unknown citation IDs
  never become valid links.
- Inventory arithmetic: sufficient stock, exact stock, shortages, missing
  rows, zero stock, invalid quantity, empty BOM, duplicate components, and
  ambiguous aliases, per `check_build_readiness`/`lookup_stock` semantics.
  Zero stock and unknown stock stay distinguishable.
- `GET /api/sops/{document_id}/sections/{section_id}?version=...` returns
  the exact original text for a real version and 404s for a missing one.
- A full browser workflow (Playwright) against the real frontend and
  backend, not just mocked UI fixtures, per C2's acceptance criteria.

## Acceptance gate

Per the C3 delivery report (`docs/agent-reports/C3-delivery.md`):
offline CI must be green with zero provider credentials present, and this
suite must assert `status` and citation shape using mocked LLM responses,
against a fresh `docker compose up` of `infra/compose.yaml`.

## Status

Implemented: `test_backend_smoke.py` against G1's standalone backend.
Blocked on the coordinator merging G1 (and eventually C1/G2/C2) into a
shared baseline this branch can build against, and then on C1 (inventory)
and G2 (retrieval) being wired into G1's `Services` implementation so the
`answered`/`ready=true` scenarios above become testable. Update this file
to link real test files as they land instead of replacing it wholesale,
so the blocked/implemented history stays visible in git.
