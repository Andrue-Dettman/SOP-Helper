-- Runs once, automatically, only on a fresh (empty) data volume, via the
-- official Postgres image's /docker-entrypoint-initdb.d convention. Idempotent
-- migrations still assume the extension exists; this just removes the manual
-- "CREATE EXTENSION" step for a fresh local checkout.
CREATE EXTENSION IF NOT EXISTS vector;
