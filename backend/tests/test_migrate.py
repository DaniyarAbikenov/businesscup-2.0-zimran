"""AUTO_MIGRATE: idempotent, waits for the advisory lock, does nothing unless asked."""
import threading
import time

from sqlalchemy import text

from app import migrate
from app.db import engine


def test_skipped_unless_enabled(monkeypatch):
    monkeypatch.delenv("AUTO_MIGRATE", raising=False)
    monkeypatch.setattr(migrate, "_done", False)
    assert migrate.run() is False


def test_runs_twice_without_error():
    assert migrate.run(force=True) is True
    assert migrate.run(force=True) is True  # nothing left to do the second time
    with engine.connect() as c:
        assert c.execute(text("select version_num from alembic_version")).scalar() == "0010"


def test_waits_for_the_advisory_lock():
    done = []
    with engine.connect() as holder:
        holder.execute(text("SELECT pg_advisory_lock(:i)"), {"i": migrate.LOCK_ID})
        t = threading.Thread(target=lambda: done.append(migrate.run(force=True)))
        t.start()
        time.sleep(1.0)
        assert t.is_alive() and not done  # blocked while another instance holds the lock
        holder.execute(text("SELECT pg_advisory_unlock(:i)"), {"i": migrate.LOCK_ID})
        holder.commit()
    t.join(15)
    assert done == [True]
