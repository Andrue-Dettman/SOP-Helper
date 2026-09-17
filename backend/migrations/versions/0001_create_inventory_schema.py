"""create inventory schema

C1's seven inventory tables, against G1's shared Alembic environment
(backend/migrations/env.py, target_metadata=app.database.Base.metadata). This is
currently the only revision; if G2's retrieval migration or a bootstrap revision
lands first, the coordinator must reset `down_revision` to chain after it instead
of leaving two revision heads.

Revision ID: c1_0001_inventory_schema
Revises:
Create Date: (set on merge)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c1_0001_inventory_schema"
down_revision = None  # set by coordinator/G1 once the bootstrap revision exists
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parts",
        sa.Column("part_id", sa.Text(), primary_key=True),
        sa.Column("sku", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False, server_default="each"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("sku", name="uq_parts_sku"),
    )

    op.create_table(
        "part_aliases",
        sa.Column("alias_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("part_id", sa.Text(), sa.ForeignKey("parts.part_id"), nullable=False),
        sa.Column("alias_text", sa.Text(), nullable=False),
        sa.UniqueConstraint("part_id", "alias_text", name="uq_part_alias_part_text"),
    )
    op.create_index("ix_part_aliases_part_id", "part_aliases", ["part_id"])

    op.create_table(
        "assemblies",
        sa.Column("assembly_id", sa.Text(), primary_key=True),
        sa.Column("sku", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("sku", name="uq_assemblies_sku"),
    )

    op.create_table(
        "assembly_aliases",
        sa.Column("alias_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "assembly_id", sa.Text(), sa.ForeignKey("assemblies.assembly_id"), nullable=False
        ),
        sa.Column("alias_text", sa.Text(), nullable=False),
        sa.UniqueConstraint("assembly_id", "alias_text", name="uq_assembly_alias_assembly_text"),
    )
    op.create_index("ix_assembly_aliases_assembly_id", "assembly_aliases", ["assembly_id"])

    op.create_table(
        "bom_lines",
        sa.Column("bom_line_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "assembly_id", sa.Text(), sa.ForeignKey("assemblies.assembly_id"), nullable=False
        ),
        sa.Column("component_part_id", sa.Text(), sa.ForeignKey("parts.part_id"), nullable=False),
        sa.Column("quantity_per_assembly", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity_per_assembly > 0", name="ck_bom_line_qty_positive"),
        sa.UniqueConstraint("assembly_id", "component_part_id", name="uq_bom_line_assembly_part"),
    )
    op.create_index("ix_bom_lines_assembly_id", "bom_lines", ["assembly_id"])

    op.create_table(
        "stock_levels",
        sa.Column("part_id", sa.Text(), sa.ForeignKey("parts.part_id"), primary_key=True),
        sa.Column("quantity_on_hand", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("quantity_on_hand >= 0", name="ck_stock_qty_nonnegative"),
    )

    op.create_table(
        "inventory_snapshot",
        sa.Column("snapshot_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "taken_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("note", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("inventory_snapshot")
    op.drop_table("stock_levels")
    op.drop_table("bom_lines")
    op.drop_table("assembly_aliases")
    op.drop_table("assemblies")
    op.drop_table("part_aliases")
    op.drop_table("parts")
