from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import packs, reminders
from ..cache import get_redis
from ..db import get_db
from ..deps import current_user
from ..models import Case, JournalEntry

router = APIRouter(prefix="/api")


@router.get("/journal")
def journal(user=Depends(current_user), db: Session = Depends(get_db)):
    entries = db.scalars(select(JournalEntry).where(JournalEntry.user_id == user.id).order_by(JournalEntry.id.desc()).limit(100)).all()
    cases = db.scalars(select(Case).where(Case.user_id == user.id).order_by(Case.id.desc())).all()
    decided = [c for c in cases if c.status == "decided"]
    reflected = [c for c in decided if c.reflection]
    today = packs.today()
    return {
        "entries": [{"id": e.id, "case_id": e.case_id, "type": e.type, "text": e.text, "created_at": e.created_at.isoformat()} for e in entries],
        "cases": [{"id": c.id, "title": c.inputs["changeTitle"], "status": c.status, "chosenOption": c.decision.option if c.decision else None,
                   "followupDue": c.decision.followup_due.isoformat() if c.decision else None, "followupDone": bool(c.followup),
                   "reflected": bool(c.reflection), "createdAt": c.created_at.isoformat()} for c in cases],
        "followups": [{"caseId": c.id, "title": c.inputs["changeTitle"], "due": c.decision.followup_due.isoformat(),
                       "overdue": c.decision.followup_due.isoformat() <= today} for c in decided if not c.followup],
        "stats": {
            "started": len(cases),
            "decided": len(decided),
            "followedUp": sum(1 for c in decided if c.followup),
            "reportedWorked": sum(1 for c in decided if c.followup and c.followup.outcome in ("worked", "partly")),
            "confidenceChange": round(sum(c.reflection.confidence_after - c.confidence_before for c in reflected) / len(reflected), 1) if reflected else None,
        },
    }


@router.get("/reminders")
def reminder_badge(user=Depends(current_user), r=Depends(get_redis)):
    return {"due": reminders.due_count(r, user.id)}
