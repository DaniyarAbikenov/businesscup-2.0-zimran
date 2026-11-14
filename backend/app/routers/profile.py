from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import packs
from ..db import get_db
from ..deps import current_user
from ..errors import ApiError
from ..msg import tr
from ..cache import get_redis
from ..models import JournalEntry, Profile
from .auth import profile_dict

router = APIRouter(prefix="/api")


@router.put("/profile")
def put_profile(body: dict, user=Depends(current_user), db: Session = Depends(get_db)):
    role = packs.get_role(body.get("roleId"))
    if not role:
        raise ApiError(400, "Choose a role")
    if body.get("tenure") not in [t["id"] for t in packs.roles_pack["tenures"]]:
        raise ApiError(400, "Choose how long you have been in the role")
    fear_ids = [f["id"] for f in packs.roles_pack["fears"]]
    fears = [f for f in body.get("fears", []) if isinstance(f, str) and f in fear_ids] if isinstance(body.get("fears"), list) else []
    industry = str(body.get("industry") or "").strip()[:80]
    fear_note = str(body.get("fearNote") or "").strip()[:500]
    p = db.get(Profile, user.id) or Profile(user_id=user.id)
    p.role_id, p.industry, p.tenure, p.fears, p.fear_note = role["id"], industry, body["tenure"], fears, fear_note
    db.add(p)
    db.add(JournalEntry(user_id=user.id, type="onboarding", text=tr("Set up profile as {role}", role=role['label']) + (tr(" in {industry}", industry=industry) if industry else "") + "."))
    db.commit()
    get_redis().set(f"role:{user.id}", p.role_id, ex=86400)
    return {"profile": profile_dict(p)}


TOUR_KEYS = ["home", "form", "guess", "results", "decided", "progress", "cases"]


@router.put("/profile/tours")
def put_tours(body: dict, user=Depends(current_user), db: Session = Depends(get_db)):
    """Which guided tours were shown. {seen: [keys]} adds keys, {disable: bool} switches tours off or on, {reset: true} starts all again."""
    p = db.get(Profile, user.id)
    if not p:
        raise ApiError(409, "Set up your profile first")
    if body.get("reset") is True:
        p.tours_seen, p.tours_disabled = [], False
    seen = body.get("seen")
    if seen is not None:
        if not isinstance(seen, list) or any(k not in TOUR_KEYS for k in seen):
            raise ApiError(400, "Unknown tour")
        p.tours_seen = sorted(set(p.tours_seen or []) | set(seen), key=TOUR_KEYS.index)
    if "disable" in body:
        if not isinstance(body["disable"], bool):
            raise ApiError(400, "Choose on or off")
        p.tours_disabled = body["disable"]
    db.commit()
    return {"toursSeen": p.tours_seen, "toursDisabled": p.tours_disabled}


@router.put("/profile/language")
def put_language(body: dict, user=Depends(current_user), db: Session = Depends(get_db)):
    from .. import i18n
    lang = body.get("language")
    if lang is not None and i18n.norm(lang) != lang:
        raise ApiError(400, "Unknown language")
    p = db.get(Profile, user.id)
    if not p:
        raise ApiError(409, "Set up your profile first")
    p.language = lang
    db.commit()
    return {"language": p.language}
