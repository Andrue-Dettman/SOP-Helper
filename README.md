# Warehouse Procedure & Inventory Assistant

Portfolio application workspace, implementation in progress across six
independent worker branches (none merged into `main` yet). As of this
writing: G1 has a real, standalone FastAPI backend; G2 has retrieval,
ingestion, and sample SOP data; G3 has an evaluation harness; C2 has a
Vite/React frontend scaffold against fixtures. C1 (inventory) hasn't
landed. This branch (C3, delivery/integration) adds the environment
template, Postgres/pgvector + backend Compose services, delivery
scripts, and CI. See [docs/operations.md](docs/operations.md) for
exactly what's real vs. still pending, and
[agents/RUN_STATUS.md](agents/RUN_STATUS.md) for the planning-phase
record.

Start with [PLAN.md](PLAN.md) for the consolidated implementation plan, [agents/ROSTER.md](agents/ROSTER.md) for the six assignments, and [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md) for scope.

The project will use fictional SOPs, parts, inventory, and bills of materials. It will not connect to an employer database. Business impact and accessibility effectiveness are not established outcomes.

The six planning workers are three OpenAI/Codex agents and three real Claude Code sessions. Their assignments, local skills, isolated Git worktrees, and reports support a later implementation phase.

## Running what exists today

```
cp .env.example .env
docker compose -f infra/compose.yaml up -d db
./scripts/db-health.sh
```

`infra/compose.yaml` also defines a `backend` service
(`infra/Dockerfile.backend`, built and verified against G1's actual
code), but `backend/` itself isn't part of this branch — it lands once
the coordinator merges `agent/g1-api` in. Once it is,
`./scripts/integration-test.sh` builds+starts db and backend, waits for
health, and runs `tests/integration/` (currently: health/ready/chat
honestly report `temporarily_unavailable`, not a fabricated answer).
There is no frontend or seed data wired into Compose yet. See
[docs/demo.md](docs/demo.md) for the planned (not yet fully runnable)
demo script and [docs/operations.md](docs/operations.md) for local
troubleshooting and the per-worker port/isolation convention.

## CI

`.github/workflows/offline.yml` runs hermetically on every push/PR
(validates `infra/compose.yaml`, lints `scripts/` with shellcheck, runs
`scripts/integration-test.sh`; no provider credentials — it no-ops
cleanly on a branch without `backend/`). `.github/workflows/live-smoke.yml`
is manual and credential-gated, and currently reports that there's
nothing meaningful to smoke-test end-to-end yet (inventory/retrieval
aren't wired into the backend) rather than faking a pass.
