"""Content packs (roles + situations) live in app/packs/*.json, not in code."""
import json
from datetime import date, timedelta
from pathlib import Path

_dir = Path(__file__).parent / "packs"
roles_pack = json.loads((_dir / "roles.json").read_text())
situations = json.loads((_dir / "situations.json").read_text())["situations"]


def get_role(role_id):
    return next((r for r in roles_pack["roles"] if r["id"] == role_id), None)


def get_situation(sid):
    return next((s for s in situations if s["id"] == sid), None)


def today() -> str:
    return date.today().isoformat()


def add_days(iso: str, n: int) -> str:
    return (date.fromisoformat(iso) + timedelta(days=n)).isoformat()


def next_weekday(iso: str) -> str:
    d = date.fromisoformat(iso)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()


def public_pack() -> dict:
    out = dict(roles_pack)
    sits = []
    for s in situations:
        qs = []
        for q in s["questions"]:
            if "defaultDaysFromNow" in q:
                q = {**q, "default": next_weekday(add_days(today(), q["defaultDaysFromNow"]))}
            qs.append(q)
        sits.append({**s, "questions": qs})
    out["situations"] = sits
    return out
