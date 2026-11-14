"""decision options come from situation packs (accept/defer/decline was only the first situation)

Revision ID: 0004
Revises: 0003
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_decisions_option", "decisions")
    op.create_check_constraint("ck_decisions_option", "decisions", "option ~ '^[a-z][a-z_]{0,19}$'")


def downgrade():
    # fails if decisions with other option keys exist, which is the safe outcome: nothing is silently dropped
    op.drop_constraint("ck_decisions_option", "decisions")
    op.create_check_constraint("ck_decisions_option", "decisions", "option IN ('accept','defer','decline')")
