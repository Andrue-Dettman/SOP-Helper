"""Create immutable SOP corpus and embedding index storage.

Revision ID: g2_0002_retrieval_schema
Revises: c1_0001_inventory_schema
"""

from alembic import op

from app.ingestion.schema import downgrade as drop_retrieval_schema
from app.ingestion.schema import upgrade as create_retrieval_schema

revision = "g2_0002_retrieval_schema"
down_revision = "c1_0001_inventory_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_retrieval_schema(op.get_bind())


def downgrade() -> None:
    drop_retrieval_schema(op.get_bind())
