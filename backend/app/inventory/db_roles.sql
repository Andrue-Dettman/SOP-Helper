-- Read-only runtime role and separate seed/migration role for the inventory tables.
-- Run once against the target database with an admin/superuser connection during
-- environment setup (G1/C3 own wiring this into the actual bootstrap and attaching
-- login credentials via env vars) -- never executed by the application itself.

-- Run with `psql -v dbname=<actual_demo_db_name>` so :dbname resolves below.
CREATE ROLE warehouse_runtime_ro NOLOGIN;
GRANT CONNECT ON DATABASE :dbname TO warehouse_runtime_ro;
GRANT USAGE ON SCHEMA public TO warehouse_runtime_ro;
GRANT SELECT ON
    parts,
    part_aliases,
    assemblies,
    assembly_aliases,
    bom_lines,
    stock_levels,
    inventory_snapshot
TO warehouse_runtime_ro;
-- G2's retrieval tables need an equivalent SELECT grant added here once they exist;
-- CONTRACTS.md calls for one shared runtime role covering every inventory/retrieval
-- table, not a second runtime role.

CREATE ROLE warehouse_seed_rw NOLOGIN;
GRANT CONNECT ON DATABASE :dbname TO warehouse_seed_rw;
GRANT USAGE ON SCHEMA public TO warehouse_seed_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON
    parts,
    part_aliases,
    assemblies,
    assembly_aliases,
    bom_lines,
    stock_levels,
    inventory_snapshot
TO warehouse_seed_rw;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO warehouse_seed_rw;

-- Neither role gets DDL rights or superuser; Alembic migrations run under a
-- separate admin/migration credential from G1's shared bootstrap.
