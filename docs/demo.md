# Demo script

The backend, real inventory/corpus data, and every non-model endpoint
run today (verified: `/api/ready`, `/api/assemblies`, real SOP section
text). Each workflow below is a real `POST /api/chat` call, so it also
needs `OPENAI_API_KEY`/`OPENAI_CHAT_MODEL` configured to get past
`temporarily_unavailable` — that live round trip has not been exercised
here (no key available in this environment); everything up to the model
call has been. There is no frontend service in Compose yet, so today
this is a `curl`-driven walkthrough, not a browser one.

All data referenced below is fictional (invented SOPs, parts, and stock);
the demo will make that explicit on screen per `docs/PROJECT_BRIEF.md`.

## Setup

1. `cp .env.example .env` and set `OPENAI_API_KEY`/`OPENAI_CHAT_MODEL`
   for a real run (leave blank to see the honest unavailable state).
2. `./scripts/migrate-and-seed.sh` (one-time per fresh volume).
3. `docker compose -f infra/compose.yaml up -d --build backend`
4. `curl http://localhost:${API_PORT:-8100}/api/ready` — confirm
   `database`/`corpus` read `ready`.
5. Once C2's frontend is wired into Compose: open
   `http://localhost:${FRONTEND_PORT}`. Until then, use
   `curl -X POST http://localhost:${API_PORT:-8100}/api/chat -d '{"message": "..."}'`.

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
