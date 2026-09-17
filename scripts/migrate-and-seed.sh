#!/usr/bin/env bash
# One-off setup for a fresh db volume in THIS compose project: runs Alembic
# migrations, then G2's SOP corpus ingestion, then C1's inventory seed.
# Never runs automatically on API startup (see backend/migrations/env.py and
# backend/app/ingestion/__main__.py) - this script is the explicit trigger.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/compose.yaml"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-warehouse-main}"
POSTGRES_USER="${POSTGRES_USER:-warehouse}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-warehouse_dev_only}"
POSTGRES_DB="${POSTGRES_DB:-warehouse}"
DB_URL="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"

if [[ ! -d "$ROOT_DIR/backend" ]]; then
  echo "backend/ not present on this branch yet; nothing to migrate/seed."
  exit 0
fi

compose() { docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" "$@"; }

compose build backend
compose up -d db
"$ROOT_DIR/scripts/db-health.sh"

echo "Running Alembic migrations..."
compose run --rm -e MIGRATION_DATABASE_URL="$DB_URL" --entrypoint python backend -m alembic upgrade head

echo "Ingesting SOP corpus (lexical mode)..."
compose run --rm -e WAREHOUSE_SEED_DATABASE_URL="$DB_URL" --entrypoint python backend -m app.ingestion --corpus data/sops --mode lexical

echo "Seeding inventory..."
compose run --rm -e WAREHOUSE_SEED_DATABASE_URL="$DB_URL" --entrypoint python backend scripts/seed_inventory.py

echo "Migrate/seed complete for compose project: $PROJECT_NAME"
