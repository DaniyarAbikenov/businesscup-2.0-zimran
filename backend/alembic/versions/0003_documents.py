"""documents and their revisions: every saved Change Request edit and client message is kept

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None
now = sa.text("now()")


def upgrade():
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.CheckConstraint("kind IN ('change_request','client_message')", name="ck_documents_kind"),
        sa.UniqueConstraint("case_id", "kind", name="uq_documents_case_kind"),
    )
    op.create_table(
        "document_revisions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("source", sa.String(10), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
    )
    # existing decisions already have a generated Change Request: give each one a document and a first revision
    op.execute("""
        INSERT INTO documents (user_id, case_id, kind, body, created_at, updated_at)
        SELECT c.user_id, d.case_id, 'change_request', d.document, d.decided_at, d.decided_at
        FROM decisions d JOIN cases c ON c.id = d.case_id""")
    op.execute("""
        INSERT INTO document_revisions (document_id, body, source, created_at)
        SELECT id, body, 'generated', created_at FROM documents""")


def downgrade():
    # the generated text stays in decisions.document; user edits and client messages are dropped
    op.drop_table("document_revisions")
    op.drop_table("documents")
