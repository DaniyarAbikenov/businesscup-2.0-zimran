"""email reminders: opt-in flag, one reminder per follow-up, day-7 nudge flag, one-click tokens

Revision ID: 0007
Revises: 0006
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("profiles", sa.Column("email_reminders", sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column("profiles", sa.Column("day7_nudge_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("decisions", sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "email_tokens",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('worked','partly','not_yet','unsubscribe')", name="ck_email_tokens_kind"),
    )


def downgrade():
    op.drop_table("email_tokens")
    op.drop_column("decisions", "reminder_sent_at")
    op.drop_column("profiles", "day7_nudge_sent_at")
    op.drop_column("profiles", "email_reminders")
