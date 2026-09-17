"""Idempotent seed/reset for the fictional demo inventory database.

Intended to run with separate seed/migration credentials, never the read-only
runtime role. Deletes and re-inserts this module's own tables inside one
transaction, then bumps `inventory_snapshot` atomically so no query can observe a
half-replaced dataset. Must only ever target the local demo database; the
`expected_database_marker` guard below is a placeholder until G1/C3 finalize how
the demo database's identity is asserted (e.g. a required name suffix or a
dedicated `is_demo` marker table).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.inventory.models import (
    Assembly,
    AssemblyAlias,
    BomLine,
    InventorySnapshot,
    Part,
    PartAlias,
    StockLevel,
)

from .fixtures import (
    ASSEMBLIES,
    ASSEMBLY_ALIASES,
    BOM_LINES,
    PART_ALIASES,
    PARTS,
    STOCK_LEVELS,
)


class WrongDatabaseError(RuntimeError):
    pass


def _assert_demo_database(session: Session, expected_database_marker: str) -> None:
    url = session.get_bind().url
    database_name = url.database or ""
    if expected_database_marker not in database_name:
        raise WrongDatabaseError(
            f"refusing to seed database {database_name!r}: "
            f"expected it to contain {expected_database_marker!r}"
        )


def reset_and_seed(session: Session, *, expected_database_marker: str = "warehouse") -> int:
    """Replace all inventory data with the fixed fictional dataset.

    Returns the new `snapshot_id`. Caller commits (or the session is already
    scoped to one transaction, per the caller's session-management convention).
    """
    _assert_demo_database(session, expected_database_marker)

    session.query(BomLine).delete()
    session.query(StockLevel).delete()
    session.query(PartAlias).delete()
    session.query(AssemblyAlias).delete()
    session.query(Part).delete()
    session.query(Assembly).delete()

    session.add_all(
        Part(part_id=p.part_id, sku=p.sku, display_name=p.display_name, unit=p.unit)
        for p in PARTS
    )
    session.add_all(
        Assembly(assembly_id=a.assembly_id, sku=a.sku, display_name=a.display_name)
        for a in ASSEMBLIES
    )
    session.flush()  # parts/assemblies must exist before their foreign keys below

    session.add_all(
        PartAlias(part_id=a.part_id, alias_text=a.alias_text) for a in PART_ALIASES
    )
    session.add_all(
        AssemblyAlias(assembly_id=a.assembly_id, alias_text=a.alias_text)
        for a in ASSEMBLY_ALIASES
    )
    session.add_all(
        BomLine(
            assembly_id=b.assembly_id,
            component_part_id=b.component_part_id,
            quantity_per_assembly=b.quantity_per_assembly,
        )
        for b in BOM_LINES
    )
    session.add_all(
        StockLevel(part_id=s.part_id, quantity_on_hand=s.quantity_on_hand) for s in STOCK_LEVELS
    )

    snapshot = InventorySnapshot(note="fictional demo dataset")
    session.add(snapshot)
    session.flush()
    return snapshot.snapshot_id
