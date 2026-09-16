# C1 — Inventory/BOM Module Plan

## Decisions

Scope: one warehouse, integer quantities, one-level assemblies (BOM lines reference parts, never other assemblies — enforced structurally by foreign keys, not just convention).

### Schema (`backend/app/inventory/`, inventory migrations)

- `parts(part_id PK text, sku unique text, display_name text, unit text default 'each', created_at timestamptz)`
- `part_aliases(alias_id PK, part_id FK->parts, alias_text text, UNIQUE(part_id, alias_text))` — `alias_text` is deliberately not globally unique; multiple parts sharing an alias is how ambiguity arises.
- `assemblies(assembly_id PK text, sku unique text, display_name text, created_at timestamptz)`
- `assembly_aliases(alias_id PK, assembly_id FK->assemblies, alias_text text, UNIQUE(assembly_id, alias_text))`
- `bom_lines(bom_line_id PK, assembly_id FK->assemblies, component_part_id FK->parts, quantity_per_assembly int CHECK(>0), UNIQUE(assembly_id, component_part_id))` — the unique constraint forces ingestion to aggregate duplicate lines or fail; no silent double-counting.
- `stock_levels(part_id FK->parts PK, quantity_on_hand int CHECK(>=0), updated_at timestamptz)` — absence of a row means unknown, not zero.
- `inventory_snapshot(snapshot_id serial PK, taken_at timestamptz, note text)` — one advancing row, bumped atomically whenever the seed/reset script replaces `stock_levels`/`bom_lines` inside a single transaction.

### Transaction/snapshot semantics

Every read (`lookup_stock`, `check_build_readiness`) opens one read-only `REPEATABLE READ` transaction, reads the current `snapshot_id`/`taken_at` first, then evaluates all components inside that same transaction so a concurrent reseed can't mix old and new rows within one call. Reseeding (`data/inventory/seed.py`, separate migration/seed credentials) wraps delete+insert+snapshot bump atomically. Runtime query credentials get `SELECT`-only grants on these six tables; nothing else.

### Missing/ambiguous data handling

- Alias matches zero parts/assemblies → `not_found`.
- Alias matches >1 distinct part/assembly → `ambiguous`, return candidate IDs/names, no quantities (caller must disambiguate before calling `check_build_readiness`).
- Part exists but no `stock_levels` row → `available=None` (unknown ≠ zero); such a component can never contribute to `ready=true`.
- Assembly exists with zero `bom_lines` → `ready=false`, explicit `reason="empty_bom"` (never trivially ready).
- `quantity` validated as a positive integer ≤ `MAX_BUILD_QUANTITY` (propose 100000) in Pydantic before any query executes.

### Typed tool results (`backend/app/inventory/schemas.py`)

```
LookupStockResult: status: ok|ambiguous|not_found|unavailable
  matches: list[PartMatch]  # part_id, display_name, sku, quantity_on_hand: int|None, unit
  snapshot_id, snapshot_taken_at

CheckBuildReadinessResult: assembly_id, requested_quantity, ready: bool
  reason: none|empty_bom|missing_stock|unknown_component
  components: list[ComponentResult]  # part_id, display_name, per_assembly_qty, required, available: int|None, shortage: int|None
  snapshot_id, snapshot_taken_at
```

### Worked example

Assembly `ASM-0001` "Widget Kit": `PRT-0001` Bolt (per_assembly=4, stock=100), `PRT-0002` Bracket (per_assembly=1, stock=15). Request 20 units: Bolt required=80, available=100, shortage=0; Bracket required=20, available=15, shortage=5. `ready=false`.

### Seed characteristics

Deterministic, fictional, checked into `data/inventory/`: ~30 parts, 6 assemblies, one-level BOMs, plus deliberate edge fixtures — one part with no `stock_levels` row, one empty-BOM assembly, one alias shared by two parts. Reset script is idempotent and touches only the demo database.

## Contract defects in v0 and fixes

1. No tool resolves an assembly name to `assembly_id`; `check_build_readiness` assumes it's already known. **Fix:** add `resolve_assembly(query)` mirroring `lookup_stock`'s `ok|ambiguous|not_found` shape.
2. `shortage = max(required - available, 0)` is undefined when `available` is unknown. **Fix:** state that shortage is `null` and readiness `false` when any component's availability is unknown.
3. No shared bound for "excessively large" quantities. **Fix:** define `MAX_BUILD_QUANTITY` once in `CONTRACTS.md` so G1's assistant loop and C1's validation agree.
4. `lookup_stock`'s ambiguous-status payload (no quantities) differs from `ok` (has quantities), undocumented. **Fix:** document as a discriminated union keyed by `status`.
5. Alias text matching (case, whitespace) is unspecified, threatening G3's determinism. **Fix:** mandate trim + case-fold normalization for alias lookups.

## Ordered tasks (future write scope)

1. Coordinate migration ID range with G1/G2; request `resolve_assembly` + `MAX_BUILD_QUANTITY` additions to `CONTRACTS.md`.
2. Write schema migration(s) for the six tables above.
3. Implement SQLAlchemy models + Pydantic schemas in `backend/app/inventory/`.
4. Implement `resolve_part`, `resolve_assembly`, `lookup_stock`, `check_build_readiness` as parameterized, transactionally-snapshotted queries.
5. Write deterministic seed data/script in `data/inventory/`, including edge-case fixtures.
6. Write acceptance tests in `tests/inventory/`.
7. Document read-only DB role/grants for G1 to wire into the runtime provider.

## File ownership

`backend/app/inventory/` (models, schemas, queries), `data/inventory/` (seed fixtures/script), `tests/inventory/`, inventory migration files within the coordinator-allocated ID range.

## Dependencies

G1: SQLAlchemy/Alembic bootstrap pattern, DB session/config, read-only credential wiring, and the contract additions above. Coordinator: migration ID range disjoint from G2's retrieval migrations. G3: needs final missing/empty-BOM/ambiguous semantics before writing `expected_inventory` fixtures.

## Acceptance tests (`tests/inventory/`, deterministic, independently specified expectations)

Exact stock (ready, all shortages 0); one short component (not ready); unknown part query (`not_found`); ambiguous alias (`ambiguous` with candidates); known part with no stock row (`available=None`, `ready=false`); empty-BOM assembly (`ready=false`, `reason=empty_bom`); duplicate BOM line at seed time (constraint violation, rejected); invalid quantities — zero, negative, fractional, over `MAX_BUILD_QUANTITY` (rejected pre-query); snapshot consistency (`check_build_readiness` reflects one `snapshot_id` across all its components even when a reseed happens between calls).

## Risks

Ambiguity-normalization rules must lock down early since they change G3's `expected_clarification` fixtures. Migration ID collisions with G2 need coordinator arbitration before either side writes files. If G1's bootstrap doesn't yet support per-module read-only DB roles, the "no model-generated SQL, read-only runtime credentials" invariant is temporarily unenforced — flag as blocking. Empty-BOM and unknown-availability semantics ripple into many eval cases; changing them late is expensive.
