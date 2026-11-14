"""Situations a person makes from their own description. Drafts are never stored; saving re-validates on the server.
The text the user wrote is never logged, only its length."""
import logging
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import llm, packs, presets
from ..cache import get_redis
from ..db import get_db
from ..deps import current_user
from ..errors import ApiError
from ..msg import tr
from ..models import Case, CustomSituation, JournalEntry, User

router = APIRouter(prefix="/api")
log = logging.getLogger("roleshift.situations")
DRAFTS_PER_DAY = 10


class DraftIn(BaseModel):
    text: str = Field(max_length=4000)
    privacyAck: bool = False


@router.post("/situations/draft")
def draft(body: DraftIn, user: User = Depends(current_user), r=Depends(get_redis)):
    if not llm.enabled():
        raise ApiError(404, "Creating a situation needs the AI, which is not configured on this server.")
    text = body.text.strip()
    if len(text) < 30:
        raise ApiError(400, "Describe the case in a few sentences (at least 30 characters).", {"text": "Too short"})
    if not body.privacyAck:
        raise ApiError(400, "Confirm that the text has no confidential information before sending it to the AI.", {"privacyAck": "Required"})
    key = f"sitdraft:{user.id}:{date.today().isoformat()}"
    n = r.incr(key)
    r.expire(key, 2 * 86400)
    if n > DRAFTS_PER_DAY:
        raise ApiError(429, tr("You used today's {n} AI drafts. Try again tomorrow.", n=DRAFTS_PER_DAY))
    try:
        preset = presets.normalize(llm.generate_preset(text, presets.engine_specs()))
    except llm.LlmError as e:
        log.warning("draft failed user=%s len=%s reason=%s", user.id, len(text), e)
        raise ApiError(502, "The AI is unavailable right now. Try again in a minute.")
    sit = presets.build(preset)
    log.info("draft user=%s len=%s engine=%s", user.id, len(text), preset["engine"])
    return {"preset": preset, "situation": packs.public_situation(sit)}


@router.post("/situations", status_code=201)
def save(body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    preset = presets.normalize(body.get("preset"))
    if presets.count(db, user.id) >= presets.MAX_PER_USER:
        raise ApiError(400, tr("You can keep up to {n} scenarios of your own. Delete one first.", n=presets.MAX_PER_USER))
    slug = presets.unique_slug(db, user.id, preset["title"])
    db.add(CustomSituation(user_id=user.id, slug=slug, engine=preset["engine"], preset=preset, source="ai"))
    db.add(JournalEntry(user_id=user.id, type="situation", text=tr("Saved a scenario of your own: {title}", title=preset['title'])))
    db.commit()
    return {"situation": packs.public_situation(presets.build(preset, slug))}


@router.delete("/situations/{slug}")
def delete(slug: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(CustomSituation).where(CustomSituation.user_id == user.id, CustomSituation.slug == slug))
    if not row:
        raise ApiError(404, "Not found")
    if db.scalar(select(Case.id).where(Case.user_id == user.id, Case.situation_id == "my-" + slug).limit(1)):
        raise ApiError(409, "Cases already use this situation, so it cannot be deleted.")
    db.delete(row)
    db.commit()
    return {"ok": True}
