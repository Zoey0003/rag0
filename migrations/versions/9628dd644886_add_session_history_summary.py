"""Add session history summary.

Revision ID: 9628dd644886
Revises: 42d2e166e591
"""

from alembic import op
import sqlalchemy as sa


revision = "9628dd644886"
down_revision = "42d2e166e591"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "memory_sessions",
        sa.Column(
            "summary",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "memory_sessions",
        sa.Column(
            "summary_until_id",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade():
    op.drop_column("memory_sessions", "summary_until_id")
    op.drop_column("memory_sessions", "summary")