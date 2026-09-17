"""Read-only inventory/BOM queries, returning G1's frozen contract types directly.

Every function accepts an `AsyncSession` that the caller already opened inside one
REPEATABLE READ, READ ONLY transaction (`app.database.Database.read_session`) -- these
functions must not open their own transaction or set isolation level themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.models import Assembly as AssemblyRef
from app.contracts.models import BuildResult, Component, Snapshot, StockMatch, StockResult

from .models import Assembly, AssemblyAlias, BomLine, InventorySnapshot, Part, PartAlias, StockLevel

MAX_CATALOG_SEARCH_LIMIT = 20

ResolveStatus = Literal["ok", "ambiguous", "not_found"]


@dataclass(frozen=True)
class EntityRef:
    id: str
    display_name: str


@dataclass(frozen=True)
class ResolveResult:
    status: ResolveStatus
    candidates: list[EntityRef]


def normalize_alias(raw: str) -> str:
    """Trim whitespace and case-fold, per CONTRACTS.md's alias normalization rule."""
    return raw.strip().casefold()


async def _current_snapshot(session: AsyncSession) -> Snapshot | None:
    row = (
        await session.scalars(
            select(InventorySnapshot).order_by(InventorySnapshot.snapshot_id.desc()).limit(1)
        )
    ).first()
    if row is None:
        return None
    return Snapshot(snapshot_id=str(row.snapshot_id), captured_at=row.taken_at)


async def resolve_part(session: AsyncSession, query: str) -> ResolveResult:
    exact = await session.get(Part, query)
    if exact is not None:
        return ResolveResult(status="ok", candidates=[EntityRef(exact.part_id, exact.display_name)])

    normalized = normalize_alias(query)
    stmt = (
        select(Part)
        .join(PartAlias, PartAlias.part_id == Part.part_id)
        .where(func.lower(func.trim(PartAlias.alias_text)) == normalized)
        .distinct()
    )
    matches = (await session.scalars(stmt)).all()
    if not matches:
        return ResolveResult(status="not_found", candidates=[])
    candidates = [EntityRef(p.part_id, p.display_name) for p in matches]
    return ResolveResult(status="ambiguous" if len(matches) > 1 else "ok", candidates=candidates)


async def search_assemblies(session: AsyncSession, query: str, limit: int = 5) -> list[EntityRef]:
    """Ranked, bounded assembly matches backing `Services.assemblies`.

    Matches an exact canonical `assembly_id` (the assistant engine resolves a
    selected/typed assembly_id through this same call) as well as partial
    display-name/alias text, ranked exact-id/exact-name > prefix > substring.
    """
    limit = max(1, min(limit, MAX_CATALOG_SEARCH_LIMIT))
    normalized = normalize_alias(query)
    if not normalized:
        return []

    pattern = f"%{normalized}%"
    rows = (
        await session.scalars(
            select(Assembly)
            .outerjoin(AssemblyAlias, AssemblyAlias.assembly_id == Assembly.assembly_id)
            .where(
                (Assembly.assembly_id == query)
                | (func.lower(Assembly.display_name).like(pattern))
                | (func.lower(func.coalesce(AssemblyAlias.alias_text, "")).like(pattern))
            )
            .distinct()
        )
    ).all()

    def rank(assembly: Assembly) -> tuple[int, str]:
        if assembly.assembly_id == query or assembly.display_name.casefold() == normalized:
            tier = 0
        elif assembly.display_name.casefold().startswith(normalized):
            tier = 1
        else:
            tier = 2
        return (tier, assembly.assembly_id)  # id tiebreak keeps results deterministic

    ranked = sorted(rows, key=rank)[:limit]
    return [EntityRef(a.assembly_id, a.display_name) for a in ranked]


async def assemblies(session: AsyncSession, query: str, limit: int) -> list[AssemblyRef]:
    matches = await search_assemblies(session, query, limit)
    return [AssemblyRef(assembly_id=m.id, label=m.display_name) for m in matches]


async def lookup_stock(session: AsyncSession, part_query: str) -> StockResult:
    snapshot = await _current_snapshot(session)
    resolution = await resolve_part(session, part_query)

    if resolution.status == "not_found":
        return StockResult(state="not_found", snapshot=snapshot, matches=[])

    if resolution.status == "ambiguous":
        parts = {c.id: await session.get(Part, c.id) for c in resolution.candidates}
        matches = [
            StockMatch(part_id=c.id, label=c.display_name, available=None, unit=parts[c.id].unit)
            for c in resolution.candidates
        ]
        return StockResult(state="ambiguous", snapshot=snapshot, matches=matches)

    part = await session.get(Part, resolution.candidates[0].id)
    stock = await session.get(StockLevel, part.part_id)
    quantity = stock.quantity_on_hand if stock is not None else None

    match = StockMatch(part_id=part.part_id, label=part.display_name, available=quantity, unit=part.unit)
    # StockResult.state == "ok" requires a known quantity; an existing part with no
    # stock row is unknown availability, not a stock success.
    state = "ok" if quantity is not None else "incomplete"
    return StockResult(state=state, snapshot=snapshot, matches=[match])


async def check_build_readiness(session: AsyncSession, assembly_id: str, quantity: int) -> BuildResult:
    snapshot = await _current_snapshot(session)
    assert snapshot is not None, "inventory_snapshot must be seeded before serving queries"

    assembly_row = await session.get(Assembly, assembly_id)
    if assembly_row is None:
        return BuildResult(
            state="not_found",
            snapshot=snapshot,
            assembly_id=assembly_id,
            requested_units=quantity,
            ready=None,
            components=[],
        )

    bom_rows = (await session.scalars(select(BomLine).where(BomLine.assembly_id == assembly_id))).all()

    if not bom_rows:
        # An empty BOM can never be ready; G1's BuildResult validator requires
        # ready=None (not False) whenever components are missing/empty.
        return BuildResult(
            state="incomplete",
            snapshot=snapshot,
            assembly_id=assembly_id,
            requested_units=quantity,
            ready=None,
            components=[],
        )

    components: list[Component] = []
    has_known_shortage = False
    has_unknown_availability = False

    for line in bom_rows:
        stock = await session.get(StockLevel, line.component_part_id)
        required = line.quantity_per_assembly * quantity
        available = stock.quantity_on_hand if stock is not None else None

        if available is None:
            shortage = None
            has_unknown_availability = True
        else:
            shortage = max(required - available, 0)
            if shortage > 0:
                has_known_shortage = True

        components.append(
            Component(
                part_id=line.component_part_id,
                per_assembly=line.quantity_per_assembly,
                required=required,
                available=available,
                shortage=shortage,
            )
        )

    if has_known_shortage:
        ready = False
        state = "incomplete" if has_unknown_availability else "ok"
    elif has_unknown_availability:
        ready = None
        state = "incomplete"
    else:
        ready = True
        state = "ok"

    return BuildResult(
        state=state,
        snapshot=snapshot,
        assembly_id=assembly_id,
        requested_units=quantity,
        ready=ready,
        components=components,
    )
