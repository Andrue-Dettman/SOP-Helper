#!/usr/bin/env bash
# Drops and recreates ONLY this compose project's database volume.
# Reads COMPOSE_PROJECT_NAME from the environment/.env so it can never
# accidentally target a different worktree's project or data.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/compose.yaml"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-warehouse-main}"

if [[ "${1:-}" != "--yes" ]]; then
  read -r -p "This deletes local Postgres data for compose project '$PROJECT_NAME' only. Continue? [y/N] " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 1
  fi
fi

echo "Resetting database for compose project: $PROJECT_NAME"
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" down -v
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d db
"$ROOT_DIR/scripts/db-health.sh"

echo "Database reset. Seed/migration steps land here once G1 (bootstrap/Alembic) and C1/G2 (seed data) are implemented."
