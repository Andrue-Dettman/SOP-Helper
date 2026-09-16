#!/usr/bin/env bash
# Waits for this worktree's Postgres service to accept connections.
# Never targets another worktree's compose project.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/compose.yaml"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-warehouse-main}"
POSTGRES_USER="${POSTGRES_USER:-warehouse}"
POSTGRES_DB="${POSTGRES_DB:-warehouse}"
ATTEMPTS="${1:-30}"

echo "Waiting for Postgres in compose project '$PROJECT_NAME'..."
for ((i = 1; i <= ATTEMPTS; i++)); do
  if docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T db \
      pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    echo "Postgres is ready."
    exit 0
  fi
  sleep 1
done

echo "Postgres did not become ready after $ATTEMPTS second(s)." >&2
exit 1
