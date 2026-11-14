"""predict first, then reveal: the guess made before the numbers, and its score computed by the server

Revision ID: 0009
Revises: 0008
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cases", sa.Column("prediction", JSONB, nullable=True))
    op.add_column("cases", sa.Column("prediction_score", JSONB, nullable=True))


def downgrade():
    op.drop_column("cases", "prediction_score")
    op.drop_column("cases", "prediction")
