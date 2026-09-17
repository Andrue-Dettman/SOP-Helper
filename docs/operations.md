# Operations

## Current status

G1 (`agent/g1-api`) has a real, standalone FastAPI backend; G2
(`agent/g2-retrieval`) has retrieval/ingestion and sample SOP data; G3
(`agent/g3-evaluation`) has an evaluation harness; C2 (`agent/c2-frontend`)
has a Vite/React scaffold against fixtures. None of this is merged into a
shared baseline yet — `main` and this branch are still at the frozen-plan
commit plus C3's own scaffolding. C1 (inventory) hasn't landed.

`infra/compose.yaml` defines `db` (Postgres/pgvector) and `backend`
(built from `infra/Dockerfile.backend`), but `backend/` itself isn't part
of this branch — it's C3's job to package it, not to own it. Everything
below that needs `backend/` (the `backend` compose service,
`scripts/integration-test.sh`, `tests/integration/`) works once the
coordinator merges `agent/g1-api` in; until then those commands/scripts
skip or fail predictably rather than silently doing nothing useful.

## Local setup

1. Copy `.env.example` to `.env` and set `COMPOSE_PROJECT_NAME` and the
   port block to your assigned worker row (see PLAN.md's "Worktree and
   merge protocol" table and `agents/ROSTER.md`). The coordinator's
   checkout uses the defaults already in `.env.example`.
2. Bring up the database:
   ```
   docker compose -f infra/compose.yaml up -d db
   ./scripts/db-health.sh
   ```
3. Once `backend/` exists on your branch, bring up the API too and run
   the integration suite: `./scripts/integration-test.sh` (builds,
   starts db+backend, waits for health, runs `tests/integration/`, tears
   down). Without `backend/` it prints a message and exits 0.
4. Tear down when done: `./scripts/teardown.sh`.

## Isolation rules

- Each worktree/worker uses its own `COMPOSE_PROJECT_NAME`, Postgres port,
  and named volume. Never point one worktree's `.env` at another
  worktree's port or project name.
- `scripts/reset-db.sh` and `scripts/teardown.sh` only ever act on
  `COMPOSE_PROJECT_NAME` from your own environment. They do not accept a
  project name argument, on purpose, so a copy-pasted command cannot reset
  someone else's database.
- `scripts/reset-db.sh` prompts before deleting data; pass `--yes` to skip
  the prompt in a script you already trust.

## Port conventions (from PLAN.md)

| Worker | API port | Frontend port | Postgres port | Compose project |
| --- | --- | --- | --- | --- |
| Coordinator | 8100 | 5200 | 5500 | `warehouse-main` |
| G1 | 8101 | 5201 | 5501 | `warehouse-g1` |
| G2 | 8102 | 5202 | 5502 | `warehouse-g2` |
| G3 | 8103 | 5203 | 5503 | `warehouse-g3` |
| C1 | 8104 | 5204 | 5504 | `warehouse-c1` |
| C2 | 8105 | 5205 | 5505 | `warehouse-c2` |
| C3 | 8106 | 5206 | 5506 | `warehouse-c3` |

These are proposed, not reserved; check availability and pick an
alternative if one is already taken locally.

## Secrets

Real `.env` files are gitignored. `OPENAI_API_KEY`/`OPENAI_CHAT_MODEL`
are read directly by `backend/app/main.py` and by the manual
`live-smoke` GitHub Actions workflow as repository secrets; offline
tests and the `offline` workflow never require them. No provider key is
ever sent to the frontend (product invariant, see `CLAUDE.md`).

## CI

- `.github/workflows/offline.yml` runs on every push/PR: validates
  `infra/compose.yaml`, lints delivery scripts with `shellcheck`, and
  runs `scripts/integration-test.sh` (a real backend smoke test once
  `backend/` is merged in; a clean no-op otherwise). Frontend
  lint/type-check/test steps are added once C2's branch is merged.
- `.github/workflows/live-smoke.yml` is manual (`workflow_dispatch`)
  only, gated on the `OPENAI_API_KEY` repository secret, and currently
  just reports whether a live run is possible — the backend runs today
  but with no real retrieval/inventory wired in yet, so there is nothing
  meaningful to smoke-test end-to-end. It is never required to pass for
  a merge.

## Troubleshooting

- **Port already in use**: another worktree, or a previous `docker
  compose` run, still holds the port. Check `docker ps` and
  `docker compose -p <project> ps`; stop the right project rather than a
  guess.
- **`docker compose config` fails in CI**: usually a YAML syntax error in
  `infra/compose.yaml` or an undefined required variable; the job has no
  `.env`, so every variable used in `infra/compose.yaml` must have a
  `${VAR:-default}` fallback.
- **Resetting your database did nothing**: confirm `COMPOSE_PROJECT_NAME`
  in your shell/`.env` matches the project you intended; the scripts
  intentionally refuse to guess.
