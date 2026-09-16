# Integration tests (planned)

No integration tests exist yet because no worker has implemented
application code: `backend/`, `frontend/`, and `data/` do not exist on any
branch as of this writing. Writing tests against nonexistent endpoints
would be fake coverage, so this directory documents the planned suite
instead.

## What this suite will exercise once G1/C1/G2/C2 land

Per `docs/CONTRACTS.md` and PLAN.md's "Required correctness checks", using
mocked provider transport (never live credentials):

- `POST /api/chat` end-to-end for the three primary workflows: procedure
  lookup with citations, passage explanation preserving mandatory steps,
  and build-readiness calculation.
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
- Provider timeout, database unavailability, and insufficient evidence
  each produce their documented explicit state, not a fabricated success.
- A full browser workflow (Playwright) against the real frontend and
  backend, not just mocked UI fixtures, per C2's acceptance criteria.

## Acceptance gate

Per the C3 delivery report (`docs/agent-reports/C3-delivery.md`):
offline CI must be green with zero provider credentials present, and this
suite must assert `status` and citation shape using mocked LLM responses,
against a fresh `docker compose up` of `infra/compose.yaml`.

## Status

Blocked on: G1 (API + bootstrap), C1 (inventory), G2 (retrieval), C2
(frontend). Update this file to link real test files as they land instead
of replacing it wholesale, so the blocked/implemented history stays
visible in git.
