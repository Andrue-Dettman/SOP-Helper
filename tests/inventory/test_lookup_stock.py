from __future__ import annotations

import pytest

from app.inventory.queries import lookup_stock

pytestmark = pytest.mark.asyncio


async def test_lookup_stock_exact_canonical_id(db_session):
    result = await lookup_stock(db_session, "PRT-0001")
    assert result.state == "ok"
    assert result.matches[0].available == 100
    assert result.snapshot is not None


async def test_lookup_stock_alias_case_and_whitespace_insensitive(db_session):
    result = await lookup_stock(db_session, "  BoLt  ")
    assert result.state == "ok"
    assert result.matches[0].part_id == "PRT-0001"


async def test_lookup_stock_unknown_query_is_not_found(db_session):
    result = await lookup_stock(db_session, "does-not-exist")
    assert result.state == "not_found"
    assert result.matches == []


async def test_lookup_stock_ambiguous_alias_returns_candidates_without_quantities(db_session):
    result = await lookup_stock(db_session, "clip")
    assert result.state == "ambiguous"
    ids = {m.part_id for m in result.matches}
    assert ids == {"PRT-0015", "PRT-0016"}
    assert all(m.available is None for m in result.matches)


async def test_lookup_stock_part_with_no_stock_row_is_incomplete_not_zero(db_session):
    # An existing part with no stock_levels row is unknown availability, which the
    # StockResult contract represents as state="incomplete", never a zero quantity.
    result = await lookup_stock(db_session, "PRT-0030")
    assert result.state == "incomplete"
    assert result.matches[0].available is None
