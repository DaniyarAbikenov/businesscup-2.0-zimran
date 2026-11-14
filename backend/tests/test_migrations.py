"""Migrations keep data: 0001 -> 0002 moves decision/reflection/follow-up into their tables and back."""
import os
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest
from sqlalchemy.engine import make_url

from app import config

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = "roleshift_migration_test"


def alembic(url, *args):
    env = {**os.environ, "DATABASE_URL": url}
    r = subprocess.run([sys.executable, "-m", "alembic", *args], cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


@pytest.fixture
def scratch_url():
    base = make_url(config.DATABASE_URL) if not isinstance(config.DATABASE_URL, str) else make_url(config.DATABASE_URL)
    admin = base.set(drivername="postgresql").render_as_string(hide_password=False)
    with psycopg.connect(admin, autocommit=True) as c:
        c.execute(f"DROP DATABASE IF EXISTS {SCRATCH}")
        c.execute(f"CREATE DATABASE {SCRATCH} ENCODING 'UTF8' TEMPLATE template0")
    url = base.set(database=SCRATCH)
    yield url.render_as_string(hide_password=False)
    with psycopg.connect(admin, autocommit=True) as c:
        c.execute(f"DROP DATABASE IF EXISTS {SCRATCH}")


def test_upgrade_and_downgrade_preserve_data(scratch_url):
    alembic(scratch_url, "upgrade", "0001")
    raw = make_url(scratch_url).set(drivername="postgresql").render_as_string(hide_password=False)
    with psycopg.connect(raw, autocommit=True) as c:
        c.execute("INSERT INTO users (email, password_hash) VALUES ('a@b.co', 'x')")
        c.execute("""INSERT INTO cases (user_id, situation_id, inputs, result, confidence_before, status, chosen_option,
                     rationale, document, decided_at, followup_due, reflection, followup)
                     VALUES (1, 's', '{}', '{}', 2, 'decided', 'accept', 'because', 'DOC', now(), '2026-11-20',
                     '{"learned":"L","different":"D","confidenceAfter":4}',
                     '{"outcome":"worked","notes":"N","at":"2026-11-15T10:00:00+00:00"}'),
                     (1, 's', '{}', '{}', 3, 'draft', null, null, null, null, null, null, null)""")

    alembic(scratch_url, "upgrade", "head")
    with psycopg.connect(raw) as c:
        assert c.execute("SELECT case_id, option, rationale, document, followup_due::text FROM decisions").fetchall() == [(1, "accept", "because", "DOC", "2026-11-20")]
        assert c.execute("SELECT learned, different, confidence_after FROM reflections").fetchall() == [("L", "D", 4)]
        assert c.execute("SELECT outcome, notes FROM followups").fetchall() == [("worked", "N")]
        assert c.execute("SELECT count(*) FROM cases").fetchone()[0] == 2
        # 0003: the existing decision got a document with a first (generated) revision
        assert c.execute("SELECT kind, body FROM documents").fetchall() == [("change_request", "DOC")]
        assert c.execute("SELECT source FROM document_revisions").fetchall() == [("generated",)]
        # constraints
        with pytest.raises(psycopg.errors.CheckViolation):
            c.execute("INSERT INTO decisions (case_id, option, document, followup_due) VALUES (2, 'Maybe!', 'd', '2026-12-01')")
        c.rollback()
        with pytest.raises(psycopg.errors.CheckViolation):
            c.execute("INSERT INTO reflections (case_id, confidence_after) VALUES (2, 9)")
        c.rollback()
        with pytest.raises(psycopg.errors.UniqueViolation):
            c.execute("INSERT INTO followups (case_id, outcome) VALUES (1, 'worked')")
        c.rollback()
        # deleting a case removes its decision, reflection and follow-up
        c.execute("DELETE FROM cases WHERE id = 1")
        assert c.execute("SELECT (SELECT count(*) FROM decisions) + (SELECT count(*) FROM reflections) + (SELECT count(*) FROM followups)").fetchone()[0] == 0
        c.rollback()

    alembic(scratch_url, "check")  # fails if models and migrations differ
    alembic(scratch_url, "downgrade", "0001")
    with psycopg.connect(raw) as c:
        row = c.execute("SELECT chosen_option, followup_due, reflection->>'learned', followup->>'outcome' FROM cases WHERE id = 1").fetchone()
        assert row == ("accept", "2026-11-20", "L", "worked")
