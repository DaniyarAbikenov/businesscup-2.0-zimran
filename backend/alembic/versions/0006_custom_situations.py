"""custom_situations: situations a user made from their own description (AI-made presets on an existing engine)

Revision ID: 0006
Revises: 0005
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "custom_situations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("slug", sa.String(40), nullable=False),
        sa.Column("engine", sa.String(30), nullable=False),
        sa.Column("preset", JSONB, nullable=False),
        sa.Column("source", sa.String(10), nullable=False, server_default="ai"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "slug", name="uq_custom_situations_user_slug"),
        sa.CheckConstraint("slug ~ '^[a-z0-9][a-z0-9-]{0,39}$'", name="ck_custom_situations_slug"),
        sa.CheckConstraint("source IN ('ai')", name="ck_custom_situations_source"),
    )


def downgrade():
    op.drop_table("custom_situations")
