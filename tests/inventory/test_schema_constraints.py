"""DB-layer constraint tests C1 owns.

Request-shape validation (positive/bounded quantity, rejecting bool/str/float
coercion) is G1's `app.contracts.models.Quantity`/`BuildArguments`, tested in
G1's own `tests/api/`, not duplicated here.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.inventory.models import BomLine

pytestmark = pytest.mark.asyncio


async def test_duplicate_bom_line_is_rejected_by_uniqueness_constraint(db_write_session):
    # ASM-0001 already has a PRT-0001 line from the seed; a second one for the
    # same (assembly_id, component_part_id) must violate uq_bom_line_assembly_part.
    db_write_session.add(
        BomLine(assembly_id="ASM-0001", component_part_id="PRT-0001", quantity_per_assembly=1)
    )
    with pytest.raises(IntegrityError):
        await db_write_session.flush()
