from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import packs
from ..db import get_db
from ..deps import current_user
from ..errors import ApiError
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
    db.add(JournalEntry(user_id=user.id, type="onboarding", text=f"Set up profile as {role['label']}" + (f" in {industry}" if industry else "") + "."))
    db.commit()
    return {"profile": profile_dict(p)}
