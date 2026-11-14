"""Follow-up reminder index in Redis (see cache.py). Postgres stays the source of truth."""
from datetime import datetime, timezone

from sqlalchemy import select

from .models import Case


def _key(uid: int) -> str:
    return f"followups:{uid}"


def _ts(iso: str) -> float:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc).timestamp()


def schedule(r, uid: int, case_id: int, due_iso: str):
    r.zadd(_key(uid), {str(case_id): _ts(due_iso)})


def clear(r, uid: int, case_id: int):
    r.zrem(_key(uid), str(case_id))


def due_count(r, uid: int) -> int:
    return r.zcount(_key(uid), "-inf", datetime.now(timezone.utc).timestamp())  # due today or earlier


def rebuild(db, r):
    rows = db.scalars(select(Case).where(Case.status == "decided")).all()
    for c in rows:
        if c.decision and not c.followup:
            schedule(r, c.user_id, c.id, c.decision.followup_due.isoformat())
