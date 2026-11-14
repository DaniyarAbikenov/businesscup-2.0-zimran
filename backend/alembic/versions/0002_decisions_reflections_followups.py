"""split decision, reflection and follow-up out of cases into their own tables

Revision ID: 0002
Revises: 0001

Data is preserved in both directions. Also: followup_due becomes a real DATE, and CHECK constraints
enforce the allowed values (options, outcomes, 1-5 confidence, case status).
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

OPTIONS = "('accept','defer','decline')"
OUTCOMES = "('worked','partly','not_yet','not_applied')"
now = sa.text("now()")


def upgrade():
    op.create_table(
        "decisions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("option", sa.String(20), nullable=False),
        sa.Column("rationale", sa.Text, nullable=False, server_default=""),
        sa.Column("document", sa.Text, nullable=False),
        sa.Column("followup_due", sa.Date, nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.CheckConstraint(f"option IN {OPTIONS}", name="ck_decisions_option"),
    )
    op.create_table(
        "reflections",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("learned", sa.Text, nullable=False, server_default=""),
        sa.Column("different", sa.Text, nullable=False, server_default=""),
        sa.Column("confidence_after", sa.SmallInteger, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.CheckConstraint("confidence_after BETWEEN 1 AND 5", name="ck_reflections_confidence"),
    )
    op.create_table(
        "followups",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.CheckConstraint(f"outcome IN {OUTCOMES}", name="ck_followups_outcome"),
    )

    # Move existing data
    op.execute("""
        INSERT INTO decisions (case_id, option, rationale, document, followup_due, decided_at)
        SELECT id, chosen_option, COALESCE(rationale, ''), COALESCE(document, ''),
               COALESCE(followup_due, to_char(now(), 'YYYY-MM-DD'))::date, COALESCE(decided_at, now())
        FROM cases WHERE status = 'decided' AND chosen_option IS NOT NULL""")
    op.execute("""
        INSERT INTO reflections (case_id, learned, different, confidence_after)
        SELECT id, COALESCE(reflection->>'learned', ''), COALESCE(reflection->>'different', ''),
               (reflection->>'confidenceAfter')::smallint
        FROM cases WHERE reflection IS NOT NULL""")
    op.execute("""
        INSERT INTO followups (case_id, outcome, notes, created_at)
        SELECT id, followup->>'outcome', COALESCE(followup->>'notes', ''),
               COALESCE((followup->>'at')::timestamptz, now())
        FROM cases WHERE followup IS NOT NULL""")

    for col in ("chosen_option", "rationale", "document", "decided_at", "followup_due", "reflection", "followup"):
        op.drop_column("cases", col)
    op.create_check_constraint("ck_cases_status", "cases", "status IN ('draft','decided')")
    op.create_check_constraint("ck_cases_confidence", "cases", "confidence_before BETWEEN 1 AND 5")


def downgrade():
    op.drop_constraint("ck_cases_confidence", "cases")
    op.drop_constraint("ck_cases_status", "cases")
    op.add_column("cases", sa.Column("chosen_option", sa.String(20)))
    op.add_column("cases", sa.Column("rationale", sa.Text))
    op.add_column("cases", sa.Column("document", sa.Text))
    op.add_column("cases", sa.Column("decided_at", sa.DateTime(timezone=True)))
    op.add_column("cases", sa.Column("followup_due", sa.String(10)))
    op.add_column("cases", sa.Column("reflection", sa.JSON))
    op.add_column("cases", sa.Column("followup", sa.JSON))
    op.execute("""
        UPDATE cases c SET chosen_option = d.option, rationale = d.rationale, document = d.document,
               decided_at = d.decided_at, followup_due = to_char(d.followup_due, 'YYYY-MM-DD')
        FROM decisions d WHERE d.case_id = c.id""")
    op.execute("""
        UPDATE cases c SET reflection = json_build_object('learned', r.learned, 'different', r.different,
               'confidenceAfter', r.confidence_after)
        FROM reflections r WHERE r.case_id = c.id""")
    op.execute("""
        UPDATE cases c SET followup = json_build_object('outcome', f.outcome, 'notes', f.notes, 'at', f.created_at)
        FROM followups f WHERE f.case_id = c.id""")
    for t in ("followups", "reflections", "decisions"):
        op.drop_table(t)
