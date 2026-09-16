# C3: Delivery and Integration Planning Report

## Ownership review

The six-way split is workable with one structural risk: both C1 (inventory) and G2 (retrieval) own migration files against the same PostgreSQL schema, and CONTRACTS.md already flags that migration IDs must be coordinator-sequenced. I recommend the coordinator maintain a single `MIGRATIONS.md` ledger (allocated ID ranges per worker) rather than letting workers self-assign, since two independent worktrees cannot see each other's in-flight migration numbers. Second, G1 owns Python dependency declarations and app bootstrap, which makes G1 a hard prerequisite for any backend integration test C3 writes — this is correct ownership, not conflict, but it fixes G1 near the front of the merge order. Third, C2's fixture-driven frontend plan is good: it removes a false dependency on the backend being live before frontend work merges. No other overlaps found; `docs/agent-reports/*` are already partitioned per worker, and C3's future scope (`infra/`, `scripts/`, `.github/`, `tests/integration/`, delivery docs) does not intersect any application module. I see no unnecessary complexity to cut at this stage — the six-way split matches the three workflows cleanly.

## Delivery decisions

- **Packaging**: Docker Compose as the primary path, one `docker-compose.yml` at repo root plus a per-service `Dockerfile`. Each worktree runs with a distinct `COMPOSE_PROJECT_NAME` (e.g., `wha-c1`, `wha-g2`) so containers, networks, and volumes never collide. Document a native (non-Docker) fallback only for backend+Postgres, since it's the harder environment; frontend `npm run dev` is already simple.
- **Isolation**: One Postgres port and volume per worktree, assigned by a documented convention (base port + role offset) in `.env.example`, not hardcoded. Each worker's Compose file targets its own database name; no worktree may point at another's DB or run migrations against it, per CONTRACTS.md.
- **CI**: GitHub Actions, two jobs. `offline` runs on every push: lint/type-check, unit tests, and the deterministic/mocked-transport integration suite — no provider credentials required, must be hermetic. `live-smoke` is manual/label-triggered only, runs against real provider credentials stored as repo secrets, and is allowed to fail open (report unavailability) rather than block merges. This matches the skill's requirement to separate liveness, DB readiness, provider configuration, and paid smoke checks.
- **Secrets**: `.env.example` enumerates every variable with placeholder values and inline comments; real `.env` files stay gitignored. Runtime DB role is read-only for inventory/retrieval queries; a separate migration/seed role with write access is used only by setup scripts, never by the running app. No model keys reach the frontend (already a product invariant).
- **README/demo honesty**: `README.md` states what runs today, what's fixture-only, and what's blocked on credentials, with explicit setup steps and no unverified claims. `docs/demo.md` is a scripted walkthrough of the three workflows against seeded data. `docs/operations.md` covers local troubleshooting, port conflicts, and resetting only your own worktree's database.

## Dependency graph

`G1 (bootstrap/contracts)` → `{G2 retrieval, C1 inventory}` (parallel, disjoint schemas) → `C2 frontend` (can start early against fixtures, but needs frozen HTTP contract before final wiring) → `G3 evaluation` (needs stable API + inventory oracle + retrieval source IDs) → `C3 integration/delivery` (last, consumes all). C3 also produces early scaffolding (empty Compose skeleton, CI skeleton, `.env.example` stub) that other workers can adopt from day one, so this isn't a strict "wait until everyone finishes" gate.

## Cross-provider review pairs

Pairing Claude and Codex workers on adjacent contract surfaces catches interface drift early: **C1 (inventory) ↔ G2 (retrieval)** review each other's migration IDs and schema boundaries; **C2 (frontend) ↔ G1 (API)** review the HTTP contract and generated types together; **C3 (delivery) ↔ G3 (evaluation)** review what "offline" vs. "live" actually means and cross-check CI gates against evaluation run categories.

## Merge order (proposed)

1. Coordinator freezes `docs/CONTRACTS.md` v1 with resolved worker feedback.
2. G1: bootstrap, dependency files, contracts module, empty endpoint stubs.
3. C1 and G2 in parallel (nonconflicting migration IDs from the coordinator's ledger).
4. C2 against fixtures (can start anytime after step 1, merges after step 3 once real endpoints exist).
5. G3 evaluation harness and case set.
6. C3 final: Compose wiring, CI activation, integration tests, README/demo docs.

## Ordered tasks (C3 future scope)

1. `.env.example` + port/volume convention.
2. `infra/docker-compose.yml` + Dockerfiles (backend, frontend, Postgres).
3. `scripts/` for seed reset, health check, per-worktree teardown.
4. `.github/workflows/offline.yml` (hermetic) and `.github/workflows/live-smoke.yml` (credential-gated).
5. `tests/integration/` exercising the three workflows end-to-end against seeded fixtures with mocked provider transport.
6. `README.md`, `docs/demo.md`, `docs/operations.md`.

## Acceptance gates

- Offline CI green with zero provider credentials present in the environment.
- A fresh checkout of any worktree can `docker compose up` and reach `/api/health` without touching another worktree's containers/DB.
- Integration tests assert `status` values and citation shape per CONTRACTS.md, using mocked LLM responses.
- README claims are checked against what CI actually runs — no "passes" language for unexecuted live checks.

## Blocked on provider credentials

Live LLM/embedding calls, the `live-smoke` CI job, and any claim about real tool-calling accuracy or latency remain blocked until real API keys are supplied; offline retrieval, inventory arithmetic, and citation-shape tests are not blocked.

## Risks

Migration ID collisions between C1/G2 if not centrally tracked; port/volume collisions if workers deviate from the convention; README overclaiming before live checks exist. All are mitigated by the ledger, the documented convention, and the offline/live CI split above.
