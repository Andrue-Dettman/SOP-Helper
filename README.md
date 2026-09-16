# Warehouse Procedure & Inventory Assistant

Portfolio application workspace. Planning is complete; **no application
code exists yet** on any of the six worker branches (`backend/`,
`frontend/`, and `data/` are all unwritten). What exists today is C3's
delivery scaffolding: an environment template, the Postgres/pgvector
Compose service, delivery scripts, and CI workflow skeletons. See
[docs/operations.md](docs/operations.md) for exactly what that can and
cannot do right now, and [agents/RUN_STATUS.md](agents/RUN_STATUS.md) for
the planning-phase record.

Start with [PLAN.md](PLAN.md) for the consolidated implementation plan, [agents/ROSTER.md](agents/ROSTER.md) for the six assignments, and [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md) for scope.

The project will use fictional SOPs, parts, inventory, and bills of materials. It will not connect to an employer database. Business impact and accessibility effectiveness are not established outcomes.

The six planning workers are three OpenAI/Codex agents and three real Claude Code sessions. Their assignments, local skills, isolated Git worktrees, and reports support a later implementation phase.

## Running what exists today

Only the database service is defined so far:

```
cp .env.example .env
docker compose -f infra/compose.yaml up -d db
./scripts/db-health.sh
```

There is no API, frontend, or seed data to exercise yet. See
[docs/demo.md](docs/demo.md) for the planned (not yet runnable) demo
script and [docs/operations.md](docs/operations.md) for local
troubleshooting and the per-worker port/isolation convention.

## CI

`.github/workflows/offline.yml` runs hermetically on every push/PR
(validates `infra/compose.yaml`, lints `scripts/` with shellcheck; no
provider credentials). `.github/workflows/live-smoke.yml` is manual and
credential-gated, and currently just reports that there is nothing to
smoke-test yet rather than faking a pass.
