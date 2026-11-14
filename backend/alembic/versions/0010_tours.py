"""guided tours: which tours a person has seen, and whether they switched them off

Revision ID: 0010
Revises: 0009
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("profiles", sa.Column("tours_seen", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("profiles", sa.Column("tours_disabled", sa.Boolean, nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column("profiles", "tours_disabled")
    op.drop_column("profiles", "tours_seen")
