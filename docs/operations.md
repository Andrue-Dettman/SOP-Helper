# Operations

## Current status

`main` merges all six worker branches: G1 (API, `backend/app/api/bootstrap.py`
composes the real services), C1 (inventory), G2 (retrieval/ingestion/SOP
corpus), G3 (evaluation harness), C2 (frontend, not yet wired into Compose),
and C3 (this delivery scaffolding). The integrated backend is real and
verified: migrated schema, seeded inventory, ingested corpus, and a
running container answering real queries with zero provider credentials.
The one piece that still needs `OPENAI_API_KEY` is an actual `/api/chat`
model call — everything else (readiness, assemblies, SOP sections) runs
on real data today.

## Local setup

1. Copy `.env.example` to `.env` and set `COMPOSE_PROJECT_NAME` and the
   port block to your assigned worker row (see PLAN.md's "Worktree and
   merge protocol" table and `agents/ROSTER.md`). The coordinator's
   checkout uses the defaults already in `.env.example`.
2. Fresh volume, one-time per environment: `./scripts/migrate-and-seed.sh`
   (builds the backend image, starts `db`, runs Alembic migrations, G2's
   corpus ingestion, and C1's inventory seed — all via
   `docker compose run`, so no local Python environment is required).
3. Bring up the integrated API: `docker compose -f infra/compose.yaml up -d --build backend`
   (this also starts `db` via `depends_on`). Check
   `curl http://localhost:${API_PORT:-8100}/api/ready` — `database` and
   `corpus` should read `ready`; `provider` reads `missing` until
   `OPENAI_API_KEY`/`OPENAI_CHAT_MODEL` are set in `.env`.
4. Run the integration suite end-to-end (migrate+seed, start backend,
   run `tests/integration/`, tear down): `./scripts/integration-test.sh`.
5. Tear down when done: `./scripts/teardown.sh`.

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

Runtime and seed/migration credentials are not yet separated:
`backend/app/inventory/db_roles.sql` defines the intended
`warehouse_runtime_ro` (read-only) and `warehouse_seed_rw` roles, but
nothing creates them yet and `RUNTIME_DATABASE_URL` currently uses the
same `warehouse` user as migrations/seeding. Flagged as an open C3/G1
follow-up in that SQL file and in `tests/integration/README.md`.

## CI

- `.github/workflows/offline.yml` runs on every push/PR: validates
  `infra/compose.yaml`, lints delivery scripts with `shellcheck`, and
  runs `scripts/integration-test.sh` — migrates, seeds, ingests, starts
  the real integrated backend, and runs 7 tests against it, all with
  zero provider credentials. Frontend lint/type-check/test steps are
  added once it's wired into Compose.
- `.github/workflows/live-smoke.yml` is manual (`workflow_dispatch`)
  only, gated on the `OPENAI_API_KEY` repository secret. Inventory and
  retrieval are real now, so once credentials are configured this is
  meant to exercise one actual `/api/chat` model round trip end-to-end;
  it currently only reports whether that's possible; see the workflow
  file's trailing comment for the exact next step. Never required to
  pass for a merge.

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
