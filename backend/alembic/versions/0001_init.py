"""initial schema

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

now = sa.text("now()")


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "profiles",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.String(50), nullable=False),
        sa.Column("industry", sa.String(80), nullable=False, server_default=""),
        sa.Column("tenure", sa.String(20), nullable=False),
        sa.Column("fears", sa.JSON, nullable=False),
        sa.Column("fear_note", sa.String(500), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
    )
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("situation_id", sa.String(80), nullable=False),
        sa.Column("inputs", sa.JSON, nullable=False),
        sa.Column("result", sa.JSON, nullable=False),
        sa.Column("confidence_before", sa.Integer, nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="draft"),
        sa.Column("chosen_option", sa.String(20)),
        sa.Column("rationale", sa.Text),
        sa.Column("document", sa.Text),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("followup_due", sa.String(10)),
        sa.Column("reflection", sa.JSON),
        sa.Column("followup", sa.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
    )
    op.create_index("ix_cases_user_id", "cases", ["user_id"])
    op.create_table(
        "journal",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="CASCADE")),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
    )
    op.create_index("ix_journal_user_id", "journal", ["user_id"])


def downgrade():
    for t in ("journal", "cases", "profiles", "users"):
        op.drop_table(t)
