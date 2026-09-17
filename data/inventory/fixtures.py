"""Deterministic, entirely fictional inventory/BOM seed data.

~30 parts, 6 one-level assemblies, and deliberate edge fixtures:
  - PRT-0030 has no stock row at all (unknown availability, not zero).
  - ASM-0006 has zero BOM lines (empty-BOM, never ready).
  - alias "clip" is shared by PRT-0015 and PRT-0016 (ambiguous lookup).
  - PRT-0030 also appears in ASM-0005's BOM, so a build check against that
    assembly demonstrates the "unknown component availability" branch.

None of this data is real warehouse stock; it exists only for this demo.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PartFixture:
    part_id: str
    sku: str
    display_name: str
    unit: str = "each"


@dataclass(frozen=True)
class PartAliasFixture:
    part_id: str
    alias_text: str


@dataclass(frozen=True)
class AssemblyFixture:
    assembly_id: str
    sku: str
    display_name: str


@dataclass(frozen=True)
class AssemblyAliasFixture:
    assembly_id: str
    alias_text: str


@dataclass(frozen=True)
class BomLineFixture:
    assembly_id: str
    component_part_id: str
    quantity_per_assembly: int


@dataclass(frozen=True)
class StockLevelFixture:
    part_id: str
    quantity_on_hand: int


PARTS: list[PartFixture] = [
    PartFixture("PRT-0001", "SKU-B-M6X20", "Bolt M6x20"),
    PartFixture("PRT-0002", "SKU-BRK-L90", "Bracket L-90"),
    PartFixture("PRT-0003", "SKU-FILM-STR", "Stretch Film Roll"),
    PartFixture("PRT-0004", "SKU-BOARD-COR", "Corner Board"),
    PartFixture("PRT-0005", "SKU-BUCKLE-STR", "Strapping Buckle"),
    PartFixture("PRT-0006", "SKU-SHAFT-ROL", "Roller Shaft"),
    PartFixture("PRT-0007", "SKU-BEAR-608ZZ", "Bearing 608ZZ"),
    PartFixture("PRT-0008", "SKU-SLEEVE-ROL", "Roller Sleeve"),
    PartFixture("PRT-0009", "SKU-PANEL-SHF", "Shelf Panel"),
    PartFixture("PRT-0010", "SKU-POST-UPR", "Upright Post"),
    PartFixture("PRT-0011", "SKU-BRACE-CRS", "Cross Brace"),
    PartFixture("PRT-0012", "SKU-FOOT-LVL", "Leveling Foot"),
    PartFixture("PRT-0013", "SKU-FRAME-CRT", "Cart Frame"),
    PartFixture("PRT-0014", "SKU-WHEEL-CST", "Caster Wheel"),
    PartFixture("PRT-0015", "SKU-CLIP-SPR", "Spring Clip"),
    PartFixture("PRT-0016", "SKU-CLIP-RET", "Retaining Clip"),
    PartFixture("PRT-0017", "SKU-WASHER-M6", "Washer M6"),
    PartFixture("PRT-0018", "SKU-NUT-M6", "Hex Nut M6"),
    PartFixture("PRT-0019", "SKU-SCREW-M4X12", "Screw M4x12"),
    PartFixture("PRT-0020", "SKU-LABEL-BIN", "Bin Label"),
    PartFixture("PRT-0021", "SKU-TAPE-PKG", "Packing Tape Roll"),
    PartFixture("PRT-0022", "SKU-GLOVE-WRK", "Work Glove Pair"),
    PartFixture("PRT-0023", "SKU-PALLET-STD", "Standard Pallet"),
    PartFixture("PRT-0024", "SKU-STRAP-RAT", "Ratchet Strap"),
    PartFixture("PRT-0025", "SKU-BIN-TOTE", "Storage Tote Bin"),
    PartFixture("PRT-0026", "SKU-HINGE-CAB", "Cabinet Hinge"),
    PartFixture("PRT-0027", "SKU-HANDLE-DRW", "Drawer Handle"),
    PartFixture("PRT-0028", "SKU-FILTER-AIR", "Air Filter Cartridge"),
    PartFixture("PRT-0029", "SKU-BELT-CNV", "Conveyor Belt Segment"),
    PartFixture("PRT-0030", "SKU-GASKET-LGY", "Legacy Gasket Seal"),
]

PART_ALIASES: list[PartAliasFixture] = [
    PartAliasFixture("PRT-0001", "bolt"),
    PartAliasFixture("PRT-0002", "bracket"),
    PartAliasFixture("PRT-0003", "stretch wrap"),
    PartAliasFixture("PRT-0007", "bearing"),
    PartAliasFixture("PRT-0013", "cart frame"),
    PartAliasFixture("PRT-0015", "clip"),
    PartAliasFixture("PRT-0016", "clip"),  # deliberately ambiguous with PRT-0015
    PartAliasFixture("PRT-0023", "pallet"),
    PartAliasFixture("PRT-0030", "gasket"),
]

ASSEMBLIES: list[AssemblyFixture] = [
    AssemblyFixture("ASM-0001", "SKU-ASM-WIDGET", "Widget Kit"),
    AssemblyFixture("ASM-0002", "SKU-ASM-PALLETWRAP", "Pallet Wrap Station Kit"),
    AssemblyFixture("ASM-0003", "SKU-ASM-CONVROLLER", "Conveyor Roller Assembly"),
    AssemblyFixture("ASM-0004", "SKU-ASM-SHELFUNIT", "Shelf Unit Kit"),
    AssemblyFixture("ASM-0005", "SKU-ASM-TOOLCART", "Tool Cart Kit"),
    AssemblyFixture("ASM-0006", "SKU-ASM-EMPTYTEST", "Empty Test Assembly"),
]

ASSEMBLY_ALIASES: list[AssemblyAliasFixture] = [
    AssemblyAliasFixture("ASM-0001", "widget kit"),
    AssemblyAliasFixture("ASM-0005", "tool cart"),
    # Deliberately not a substring of "Conveyor Roller Assembly": exercises
    # alias-only catalog search, not just a display-name match.
    AssemblyAliasFixture("ASM-0003", "roller line"),
]

BOM_LINES: list[BomLineFixture] = [
    # ASM-0001 Widget Kit — the worked example from the C1 planning report.
    BomLineFixture("ASM-0001", "PRT-0001", 4),
    BomLineFixture("ASM-0001", "PRT-0002", 1),
    # ASM-0002 Pallet Wrap Station Kit
    BomLineFixture("ASM-0002", "PRT-0003", 2),
    BomLineFixture("ASM-0002", "PRT-0004", 4),
    BomLineFixture("ASM-0002", "PRT-0005", 8),
    # ASM-0003 Conveyor Roller Assembly
    BomLineFixture("ASM-0003", "PRT-0006", 1),
    BomLineFixture("ASM-0003", "PRT-0007", 2),
    BomLineFixture("ASM-0003", "PRT-0008", 1),
    # ASM-0004 Shelf Unit Kit
    BomLineFixture("ASM-0004", "PRT-0009", 4),
    BomLineFixture("ASM-0004", "PRT-0010", 4),
    BomLineFixture("ASM-0004", "PRT-0011", 8),
    BomLineFixture("ASM-0004", "PRT-0012", 4),
    # ASM-0005 Tool Cart Kit — includes PRT-0030, which has no stock row.
    BomLineFixture("ASM-0005", "PRT-0013", 1),
    BomLineFixture("ASM-0005", "PRT-0014", 4),
    BomLineFixture("ASM-0005", "PRT-0002", 2),
    BomLineFixture("ASM-0005", "PRT-0030", 1),
    # ASM-0006 Empty Test Assembly — intentionally no BOM lines at all.
]

# PRT-0030 is deliberately excluded: no stock_levels row means unknown, not zero.
STOCK_LEVELS: list[StockLevelFixture] = [
    StockLevelFixture("PRT-0001", 100),
    StockLevelFixture("PRT-0002", 15),
    StockLevelFixture("PRT-0003", 40),
    StockLevelFixture("PRT-0004", 200),
    StockLevelFixture("PRT-0005", 500),
    StockLevelFixture("PRT-0006", 12),
    StockLevelFixture("PRT-0007", 24),
    StockLevelFixture("PRT-0008", 12),
    StockLevelFixture("PRT-0009", 60),
    StockLevelFixture("PRT-0010", 60),
    StockLevelFixture("PRT-0011", 120),
    StockLevelFixture("PRT-0012", 60),
    StockLevelFixture("PRT-0013", 5),
    StockLevelFixture("PRT-0014", 20),
    StockLevelFixture("PRT-0015", 300),
    StockLevelFixture("PRT-0016", 300),
    StockLevelFixture("PRT-0017", 1000),
    StockLevelFixture("PRT-0018", 1000),
    StockLevelFixture("PRT-0019", 800),
    StockLevelFixture("PRT-0020", 2000),
    StockLevelFixture("PRT-0021", 150),
    StockLevelFixture("PRT-0022", 90),
    StockLevelFixture("PRT-0023", 40),
    StockLevelFixture("PRT-0024", 75),
    StockLevelFixture("PRT-0025", 110),
    StockLevelFixture("PRT-0026", 220),
    StockLevelFixture("PRT-0027", 220),
    StockLevelFixture("PRT-0028", 65),
    StockLevelFixture("PRT-0029", 8),
    # PRT-0030 intentionally omitted.
]
