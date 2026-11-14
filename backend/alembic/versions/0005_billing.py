"""pricing: purchases (the 90-day pass) and a flag for demo sample cases

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cases", sa.Column("seeded", sa.Boolean, nullable=False, server_default=sa.false()))
    # existing demo users' sample cases do not count toward the free limit
    op.execute("UPDATE cases SET seeded = true WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@demo.roleshift.local')")
    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("plan", sa.String(30), nullable=False),
        sa.Column("amount_cents", sa.Integer, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="usd"),
        sa.Column("provider", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("provider IN ('test','stripe')", name="ck_purchases_provider"),
        sa.CheckConstraint("amount_cents >= 0", name="ck_purchases_amount"),
    )


def downgrade():
    op.drop_table("purchases")
    op.drop_column("cases", "seeded")
