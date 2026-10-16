"""Add account credentials and revocable login tokens."""

from alembic import op
import sqlalchemy as sa

revision = "a14b20261014"
down_revision = "8d9c1313c00b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("memory_users", sa.Column("username", sa.String(64), nullable=True))
    op.add_column("memory_users", sa.Column("password_hash", sa.String(256), nullable=True))
    op.create_unique_constraint("uq_memory_users_username", "memory_users", ["username"])
    op.create_table(
        "auth_tokens",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("memory_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])


def downgrade():
    op.drop_table("auth_tokens")
    op.drop_constraint("uq_memory_users_username", "memory_users", type_="unique")
    op.drop_column("memory_users", "password_hash")
    op.drop_column("memory_users", "username")
