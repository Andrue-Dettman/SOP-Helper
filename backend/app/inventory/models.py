"""SQLAlchemy ORM models for the seeded inventory/BOM schema (single warehouse, one-level BOMs).

Uses G1's shared declarative `Base` (`app.database.Base`) so these tables live in the
same metadata as the rest of the application and under one Alembic environment.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Part(Base):
    __tablename__ = "parts"

    part_id: Mapped[str] = mapped_column(Text, primary_key=True)
    sku: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False, server_default="each")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    aliases: Mapped[list["PartAlias"]] = relationship(back_populates="part")
    stock_level: Mapped["StockLevel | None"] = relationship(back_populates="part")


class PartAlias(Base):
    __tablename__ = "part_aliases"
    __table_args__ = (UniqueConstraint("part_id", "alias_text", name="uq_part_alias_part_text"),)

    alias_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    part_id: Mapped[str] = mapped_column(ForeignKey("parts.part_id"), nullable=False)
    alias_text: Mapped[str] = mapped_column(Text, nullable=False)

    part: Mapped["Part"] = relationship(back_populates="aliases")


class Assembly(Base):
    __tablename__ = "assemblies"

    assembly_id: Mapped[str] = mapped_column(Text, primary_key=True)
    sku: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    aliases: Mapped[list["AssemblyAlias"]] = relationship(back_populates="assembly")
    bom_lines: Mapped[list["BomLine"]] = relationship(back_populates="assembly")


class AssemblyAlias(Base):
    __tablename__ = "assembly_aliases"
    __table_args__ = (
        UniqueConstraint("assembly_id", "alias_text", name="uq_assembly_alias_assembly_text"),
    )

    alias_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assembly_id: Mapped[str] = mapped_column(ForeignKey("assemblies.assembly_id"), nullable=False)
    alias_text: Mapped[str] = mapped_column(Text, nullable=False)

    assembly: Mapped["Assembly"] = relationship(back_populates="aliases")


class BomLine(Base):
    __tablename__ = "bom_lines"
    __table_args__ = (
        UniqueConstraint("assembly_id", "component_part_id", name="uq_bom_line_assembly_part"),
        CheckConstraint("quantity_per_assembly > 0", name="ck_bom_line_qty_positive"),
    )

    bom_line_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assembly_id: Mapped[str] = mapped_column(ForeignKey("assemblies.assembly_id"), nullable=False)
    component_part_id: Mapped[str] = mapped_column(ForeignKey("parts.part_id"), nullable=False)
    quantity_per_assembly: Mapped[int] = mapped_column(Integer, nullable=False)

    assembly: Mapped["Assembly"] = relationship(back_populates="bom_lines")
    component_part: Mapped["Part"] = relationship()


class StockLevel(Base):
    __tablename__ = "stock_levels"
    __table_args__ = (CheckConstraint("quantity_on_hand >= 0", name="ck_stock_qty_nonnegative"),)

    part_id: Mapped[str] = mapped_column(ForeignKey("parts.part_id"), primary_key=True)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    part: Mapped["Part"] = relationship(back_populates="stock_level")


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshot"

    snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
