"""Runs C1's idempotent inventory seed against the local demo database.

Fills the placeholder C1 left in data/inventory/seed.py ("expected_database_marker
guard below is a placeholder until G1/C3 finalize how the demo database's
identity is asserted") with an actual invocation, owned by C3 since it's a
delivery/ops concern rather than domain logic.

Requires WAREHOUSE_SEED_DATABASE_URL (the same variable and database-identity
convention backend/app/ingestion/__main__.py uses for the SOP corpus), pointed
at an already-migrated local demo database. Never used against a shared or
production database; never invoked from application startup.

Usage (from repo root, with backend/ importable):
    WAREHOUSE_SEED_DATABASE_URL=postgresql+psycopg://... \\
        PYTHONPATH=backend python scripts/seed_inventory.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.inventory.seed import reset_and_seed  # noqa: E402


def validate_demo_url(value: str):
    url = make_url(value)
    if (url.drivername != "postgresql+psycopg" or url.host not in ("localhost", "127.0.0.1", "db")
            or not url.database or not (url.database == "warehouse" or url.database.startswith("warehouse_"))):
        raise ValueError("Seeding requires an explicitly configured local warehouse demo database")
    return url


def main() -> int:
    value = os.environ.get("WAREHOUSE_SEED_DATABASE_URL", "")
    if not value:
        print("WAREHOUSE_SEED_DATABASE_URL is required.", file=sys.stderr)
        return 1
    try:
        url = validate_demo_url(value)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    engine = create_engine(url)
    try:
        with Session(engine) as session:
            count = reset_and_seed(session)
            session.commit()
    finally:
        engine.dispose()
    print(f"Inventory seeded: {count} row(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
