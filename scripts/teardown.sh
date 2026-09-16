#!/usr/bin/env bash
# Stops and removes ONLY this compose project's containers, network, and
# volumes. Never affects another worktree's services.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/compose.yaml"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-warehouse-main}"

echo "Tearing down compose project: $PROJECT_NAME"
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" down -v
