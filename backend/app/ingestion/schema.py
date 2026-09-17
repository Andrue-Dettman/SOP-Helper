"""Retrieval schema body, awaiting a coordinator-allocated Alembic revision.

Only an explicit migration/test call executes DDL. Runtime never calls this module's
upgrade/downgrade functions. The predecessor observed in C1 is c1_0001_inventory_schema.
"""

import sqlalchemy as sa
from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw):
        return 'vector'


metadata = sa.MetaData()
documents = sa.Table('sop_documents', metadata,
    sa.Column('document_id', sa.Text, primary_key=True),
    sa.Column('version', sa.Text, primary_key=True),
    sa.Column('checksum', sa.Text, nullable=False),
    sa.Column('source', sa.Text, nullable=False))
sections = sa.Table('sop_sections', metadata,
    sa.Column('document_id', sa.Text, primary_key=True),
    sa.Column('version', sa.Text, primary_key=True),
    sa.Column('section_id', sa.Text, primary_key=True),
    sa.Column('title', sa.Text, nullable=False), sa.Column('text', sa.Text, nullable=False),
    sa.ForeignKeyConstraint(['document_id', 'version'], ['sop_documents.document_id', 'sop_documents.version']))
chunks = sa.Table('sop_chunks', metadata,
    sa.Column('chunk_id', sa.Text, primary_key=True),
    sa.Column('document_id', sa.Text, nullable=False), sa.Column('version', sa.Text, nullable=False),
    sa.Column('section_id', sa.Text, nullable=False), sa.Column('chunker_version', sa.Text, nullable=False),
    sa.ForeignKeyConstraint(['document_id', 'version', 'section_id'],
                           ['sop_sections.document_id', 'sop_sections.version', 'sop_sections.section_id']))
generations = sa.Table('sop_generations', metadata,
    sa.Column('generation_id', sa.Text, primary_key=True), sa.Column('provider', sa.Text, nullable=False),
    sa.Column('model', sa.Text, nullable=False), sa.Column('dimension', sa.Integer, nullable=False),
    sa.CheckConstraint('dimension BETWEEN 1 AND 16000', name='ck_sop_dimension'))
revisions = sa.Table('sop_revisions', metadata,
    sa.Column('revision', sa.Text, primary_key=True), sa.Column('chunker_version', sa.Text, nullable=False),
    sa.Column('generation_id', sa.Text, sa.ForeignKey('sop_generations.generation_id'), nullable=True))
membership = sa.Table('sop_revision_documents', metadata,
    sa.Column('revision', sa.Text, sa.ForeignKey('sop_revisions.revision'), primary_key=True),
    sa.Column('document_id', sa.Text, primary_key=True), sa.Column('version', sa.Text, primary_key=True),
    sa.Column('is_current', sa.Boolean, nullable=False),
    sa.ForeignKeyConstraint(['document_id', 'version'], ['sop_documents.document_id', 'sop_documents.version']))
revision_chunks = sa.Table('sop_revision_chunks', metadata,
    sa.Column('revision', sa.Text, sa.ForeignKey('sop_revisions.revision'), primary_key=True),
    sa.Column('chunk_id', sa.Text, sa.ForeignKey('sop_chunks.chunk_id'), primary_key=True))
embeddings = sa.Table('sop_embeddings', metadata,
    sa.Column('generation_id', sa.Text, sa.ForeignKey('sop_generations.generation_id'), primary_key=True),
    sa.Column('chunk_id', sa.Text, sa.ForeignKey('sop_chunks.chunk_id'), primary_key=True),
    sa.Column('embedding', Vector(), nullable=False))
active = sa.Table('sop_active_revision', metadata,
    sa.Column('singleton', sa.Integer, primary_key=True),
    sa.Column('revision', sa.Text, sa.ForeignKey('sop_revisions.revision'), nullable=False),
    sa.CheckConstraint('singleton = 1', name='ck_sop_single_active'))


def upgrade(connection):
    """Privileged migration body. Coordinator wraps this in the allocated revision."""
    connection.execute(sa.text('CREATE EXTENSION IF NOT EXISTS vector'))
    metadata.create_all(connection)


def downgrade(connection):
    """Only G2 tables; never remove the shared vector extension."""
    metadata.drop_all(connection)
