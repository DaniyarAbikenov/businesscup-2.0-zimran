"""profiles.language: the user's chosen language (en, ru, kk); null means automatic

Revision ID: 0008
Revises: 0007
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("profiles", sa.Column("language", sa.String(2), nullable=True))
    op.create_check_constraint("ck_profiles_language", "profiles", "language IS NULL OR language IN ('en','ru','kk')")


def downgrade():
    op.drop_constraint("ck_profiles_language", "profiles")
    op.drop_column("profiles", "language")
