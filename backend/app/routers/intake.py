"""POST /api/intake: "describe your situation in your own words".
Nothing is stored: the result only pre-fills the form, and the user reviews it before creating a case.
The user's text is never logged, only its length and which path was used."""
import logging
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import intake, llm, packs
from ..cache import get_redis
from ..deps import current_user
from ..errors import ApiError
from ..models import User

router = APIRouter(prefix="/api")
log = logging.getLogger("roleshift.intake")
AI_PER_DAY = 20


class IntakeIn(BaseModel):
    text: str = Field(max_length=4000)
    useAi: bool = False
    privacyAck: bool = False


@router.post("/intake")
def describe(body: IntakeIn, user: User = Depends(current_user), r=Depends(get_redis)):
    text = body.text.strip()
    if len(text) < 20:
        raise ApiError(400, "Describe the situation in a few sentences (at least 20 characters).", {"text": "Too short"})
    if body.useAi and not body.privacyAck:
        raise ApiError(400, "Confirm that the text has no confidential information before sending it to the AI.",
                       {"privacyAck": "Required"})

    note = None
    if body.useAi and not llm.enabled():
        note = "AI reading is not configured on this server, so we matched your text by keywords."
    elif body.useAi:
        key = f"intake:ai:{user.id}:{date.today().isoformat()}"
        n = r.incr(key)
        r.expire(key, 2 * 86400)
        if n > AI_PER_DAY:
            note = f"You used today's {AI_PER_DAY} AI readings, so we matched your text by keywords."
        else:
            try:
                proposal = llm.extract_situation(text, intake.catalog(), packs.today())
                out = intake.from_ai(text, proposal)
                log.info("intake user=%s len=%s source=%s situation=%s filled=%s",
                         user.id, len(text), out["source"], out["situationId"], len(out["filled"]))
                return out
            except llm.LlmError as e:
                log.warning("intake ai failed user=%s len=%s reason=%s", user.id, len(text), e)
                note = "The AI is unavailable right now, so we matched your text by keywords."
    out = intake.from_keywords(text, note)
    log.info("intake user=%s len=%s source=keywords situation=%s", user.id, len(text), out["situationId"])
    return out
