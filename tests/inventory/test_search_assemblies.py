from __future__ import annotations

import pytest

from app.inventory.queries import assemblies, search_assemblies

pytestmark = pytest.mark.asyncio


async def test_exact_canonical_id_is_found(db_session):
    # The assistant engine resolves a selected/typed assembly_id through this same
    # call, so an exact canonical ID must match even though it isn't a display name.
    results = await search_assemblies(db_session, "ASM-0001", limit=5)
    assert results[0].id == "ASM-0001"


async def test_exact_display_name_match_ranks_first(db_session):
    results = await search_assemblies(db_session, "Widget Kit", limit=5)
    assert results[0].id == "ASM-0001"


async def test_prefix_match_beats_substring_match(db_session):
    # "Tool Cart Kit" starts with "tool"; nothing else in the fixture set does.
    results = await search_assemblies(db_session, "tool", limit=5)
    assert results[0].id == "ASM-0005"


async def test_alias_only_match_is_still_found(db_session):
    # "roller line" is an alias for ASM-0003 and is not a substring of its own
    # display name ("Conveyor Roller Assembly"), so this only works via the alias join.
    results = await search_assemblies(db_session, "roller line", limit=5)
    assert [r.id for r in results] == ["ASM-0003"]


async def test_limit_is_respected_and_clamped(db_session):
    # "kit" matches exactly 4 fixture assemblies by display name.
    all_matches = await search_assemblies(db_session, "kit", limit=20)
    assert len(all_matches) == 4

    capped = await search_assemblies(db_session, "kit", limit=2)
    assert len(capped) == 2

    over_max = await search_assemblies(db_session, "kit", limit=999)
    assert len(over_max) == 4  # clamped to 20, but only 4 rows exist


async def test_blank_query_returns_no_results(db_session):
    assert await search_assemblies(db_session, "   ", limit=5) == []


async def test_unmatched_query_returns_empty_list(db_session):
    assert await search_assemblies(db_session, "nonexistent-thing", limit=5) == []


async def test_assemblies_wraps_matches_as_contract_type(db_session):
    results = await assemblies(db_session, "Widget Kit", 5)
    assert results[0].assembly_id == "ASM-0001"
    assert results[0].label == "Widget Kit"
