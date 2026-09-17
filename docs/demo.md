# Demo script (planned, not runnable yet)

Nothing below can be run today. `backend/`, `frontend/`, and seed data do
not exist on any branch yet; only delivery scaffolding
(`infra/compose.yaml`, `.env.example`, `scripts/`, CI) has been built so
far. This is the intended walkthrough once G1 (API), C1 (inventory), G2
(retrieval), and C2 (frontend) land, kept here so the demo shape is
decided before the UI is built around it.

All data referenced below is fictional (invented SOPs, parts, and stock);
the demo will make that explicit on screen per `docs/PROJECT_BRIEF.md`.

## Setup (once implemented)

1. `cp .env.example .env`
2. `docker compose -f infra/compose.yaml up -d --build`
3. `./scripts/db-health.sh`
4. Open the frontend at `http://localhost:${FRONTEND_PORT}`.

## Workflow 1: procedure lookup

Ask "How do I receive a delivery?" Expect short ordered steps with links
to the exact sample-SOP passages they came from, and the original source
text available alongside the plain-language version.

## Workflow 2: passage explanation

Select a step from the retrieved procedure and ask what it means. Expect
an explanation that keeps every mandatory action, quantity, and
warning/escalation instruction from the source, with the original text
still visible for comparison.

## Workflow 3: build-readiness

Ask "Can we assemble 20 units of Kit A?" Expect a computed
availability/shortage result from the seeded database (not the model's
own arithmetic), with the dataset snapshot identity shown.

## Workflow 4: combined question

Ask a question that needs both a shortage calculation and its applicable
procedure. Expect the response to keep the computed inventory result and
the cited procedure separately labeled — a missing procedure must not
turn into an invented one just because the stock lookup succeeded.

## What "done" looks like for this script

Every step above runs against the real local stack (no fixture
substitution), citations resolve to real source passages, inventory
numbers are independently verifiable against the seed data, and the
screen states plainly that the data is fictional. See
`docs/agent-reports/G3-evaluation.md` for the measured evaluation results
once a live run exists — this script is a walkthrough, not evidence.
