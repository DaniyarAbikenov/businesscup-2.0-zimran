"""Opt-in migration on start (AUTO_MIGRATE=true), for hosts where you cannot run `alembic upgrade head` yourself (Vercel).
Runs once per process. A Postgres advisory lock makes concurrent cold starts wait for each other, so two instances never
migrate at the same time; the second one finds nothing left to do. Fails soft: an error is logged and the app still starts."""
import logging
import os

from sqlalchemy import text

from . import config
from .db import engine

log = logging.getLogger("roleshift.migrate")
LOCK_ID = 727354101  # arbitrary constant shared by every instance of this app
_done = False


def run(force: bool = False) -> bool:
    """Returns True when the schema is at head (or was just brought there), False when skipped or failed."""
    global _done
    if _done and not force:
        return True
    if os.environ.get("AUTO_MIGRATE", "").lower() != "true" and not force:
        return False
    from alembic import command
    from alembic.config import Config
    here = os.path.dirname(os.path.abspath(__file__))
    cfg = Config()
    cfg.set_main_option("script_location", os.path.join(here, "..", "alembic"))
    try:
        with engine.connect() as lock:  # the lock lives as long as this connection is open
            lock.execute(text("SELECT pg_advisory_lock(:i)"), {"i": LOCK_ID})
            try:
                command.upgrade(cfg, "head")
            finally:
                lock.execute(text("SELECT pg_advisory_unlock(:i)"), {"i": LOCK_ID})
                lock.commit()
        _done = True
        log.info("migrations are at head")
        return True
    except Exception as e:
        log.error("auto migration failed: %s", e)
        return False
