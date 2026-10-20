"""Add personal document ownership and import manifest.

Revision ID: d20261019a01
Revises: 1cf2b2a73698
"""
from alembic import op
import sqlalchemy as sa

revision = "d20261019a01"
down_revision = "1cf2b2a73698"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("active_source", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["memory_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "filename", name="uq_document_owner_filename"),
    )
    op.create_index("ix_knowledge_documents_owner_id", "knowledge_documents", ["owner_id"])


def downgrade():
    op.drop_index("ix_knowledge_documents_owner_id", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
