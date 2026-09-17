#!/usr/bin/env bash
# Builds/starts db+backend for THIS worktree's compose project, runs
# tests/integration against the real containers, and always tears down
# afterward. Skips cleanly if backend/ hasn't been merged into this
# branch yet, so it never fails CI on a branch that doesn't have it.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/compose.yaml"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-warehouse-main}"
API_PORT="${API_PORT:-8100}"

if [[ ! -d "$ROOT_DIR/backend" ]]; then
  echo "backend/ not present on this branch yet; skipping integration tests."
  exit 0
fi

cleanup() {
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" down -v
}
trap cleanup EXIT

docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --build db backend
"$ROOT_DIR/scripts/db-health.sh"

echo "Waiting for backend at http://localhost:${API_PORT}/api/health ..."
for _ in $(seq 1 30); do
  if curl -sf "http://localhost:${API_PORT}/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -sf "http://localhost:${API_PORT}/api/health" >/dev/null || {
  echo "Backend did not become healthy." >&2
  exit 1
}

python3 -m pip install --quiet -r "$ROOT_DIR/tests/integration/requirements.txt"
API_PORT="$API_PORT" python3 -m pytest "$ROOT_DIR/tests/integration" -v
