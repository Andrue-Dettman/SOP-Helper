# Warehouse Procedure & Inventory Assistant

Portfolio application workspace. `main` now merges all six worker
branches: G1 (FastAPI backend, bootstrap/integration factory), C1
(inventory/BOM), G2 (retrieval, ingestion, sample SOP corpus), G3
(evaluation harness), C2 (frontend against fixtures), and C3
(delivery: this scaffolding). The integrated backend is real and
verified end-to-end — migrated schema, seeded inventory, ingested
corpus, answering real queries — with zero provider credentials. The
one piece still needing `OPENAI_API_KEY` is an actual `/api/chat` model
call. See [docs/operations.md](docs/operations.md) for exactly what's
real vs. still pending, and [agents/RUN_STATUS.md](agents/RUN_STATUS.md)
for the planning-phase record.

Start with [PLAN.md](PLAN.md) for the consolidated implementation plan, [agents/ROSTER.md](agents/ROSTER.md) for the six assignments, and [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md) for scope.

The project will use fictional SOPs, parts, inventory, and bills of materials. It will not connect to an employer database. Business impact and accessibility effectiveness are not established outcomes.

## Running what exists today

```
cp .env.example .env
./scripts/migrate-and-seed.sh        # one-time per fresh volume
docker compose -f infra/compose.yaml up -d --build backend
curl http://localhost:8100/api/ready # database & corpus: ready; provider: missing
```

`./scripts/integration-test.sh` runs the same migrate/seed/build/start
sequence and then runs `tests/integration/` (7 tests: health, readiness,
real assembly search, real SOP section text, missing-version 404,
honest chat-unavailable, and request validation) against the live
container. There is no frontend service wired into Compose yet (C2's
Vite dev-server container setup is still open). See
[docs/demo.md](docs/demo.md) for the demo script (runnable today except
the model-generated portions) and [docs/operations.md](docs/operations.md)
for local troubleshooting and the per-worker port/isolation convention.

## CI

`.github/workflows/offline.yml` runs hermetically on every push/PR: validates
`infra/compose.yaml`, lints scripts with shellcheck, runs each backend
worker's own test suite (G1/G2/G3), runs the real integrated-backend
integration suite, and runs the frontend's lint/typecheck/test — no
provider credentials anywhere. `.github/workflows/live-smoke.yml` is
manual and credential-gated: it migrates/seeds/starts the real backend
and exercises one actual `/api/chat` round trip when `OPENAI_API_KEY` is
configured, and otherwise reports that no live check ran rather than
faking a pass.
