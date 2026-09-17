from __future__ import annotations

import pytest

from app.inventory.queries import check_build_readiness

pytestmark = pytest.mark.asyncio


async def test_sufficient_stock_is_ready(db_session):
    # ASM-0002 Pallet Wrap Station Kit at a small quantity: all components sufficient.
    result = await check_build_readiness(db_session, "ASM-0002", 5)
    assert result.state == "ok"
    assert result.ready is True
    assert all(c.shortage == 0 for c in result.components)


async def test_worked_example_widget_kit_20_units_has_one_shortage(db_session):
    # From the C1 planning report: Bolt required=80/avail=100/shortage=0,
    # Bracket required=20/avail=15/shortage=5 -> known shortage, but all data known.
    result = await check_build_readiness(db_session, "ASM-0001", 20)
    assert result.state == "ok"
    assert result.ready is False

    by_part = {c.part_id: c for c in result.components}
    bolt = by_part["PRT-0001"]
    assert (bolt.required, bolt.available, bolt.shortage) == (80, 100, 0)

    bracket = by_part["PRT-0002"]
    assert (bracket.required, bracket.available, bracket.shortage) == (20, 15, 5)


async def test_unknown_component_availability_yields_incomplete_null_readiness(db_session):
    # ASM-0005 Tool Cart Kit includes PRT-0030, which has no stock row, and no
    # component has a *known* shortage at a small quantity -> ready is null.
    result = await check_build_readiness(db_session, "ASM-0005", 1)
    assert result.state == "incomplete"
    assert result.ready is None

    by_part = {c.part_id: c for c in result.components}
    gasket = by_part["PRT-0030"]
    assert gasket.available is None
    assert gasket.shortage is None


async def test_known_shortage_with_unknown_component_still_reports_false_and_incomplete(db_session):
    # Same assembly at a large quantity: several components now have a *known*
    # shortage, even though PRT-0030's availability is still unknown.
    result = await check_build_readiness(db_session, "ASM-0005", 100)
    assert result.state == "incomplete"
    assert result.ready is False

    by_part = {c.part_id: c for c in result.components}
    assert by_part["PRT-0014"].shortage == 380  # required 400, available 20
    assert by_part["PRT-0030"].available is None
    assert by_part["PRT-0030"].shortage is None


async def test_empty_bom_assembly_is_never_ready(db_session):
    # G1's BuildResult validator requires ready=None (not False) whenever there are
    # no components at all -- "missing" data, not a definite known shortage.
    result = await check_build_readiness(db_session, "ASM-0006", 1)
    assert result.state == "incomplete"
    assert result.ready is None
    assert result.components == []


async def test_unknown_assembly_id_is_not_found(db_session):
    result = await check_build_readiness(db_session, "ASM-9999", 1)
    assert result.state == "not_found"
    assert result.ready is None
    assert result.components == []


async def test_snapshot_identity_is_present_and_consistent_within_one_call(db_session):
    result = await check_build_readiness(db_session, "ASM-0001", 1)
    assert result.snapshot.snapshot_id is not None
    assert result.snapshot.captured_at is not None
