from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import packs, reminders
from ..cache import get_redis
from ..db import get_db
from ..deps import current_user
from ..documents import doc_label
from ..models import Case, Document, JournalEntry

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
        "cases": [{"id": c.id, "title": packs.case_title(c.situation_id, c.inputs), "status": c.status, "chosenOption": c.decision.option if c.decision else None,
                   "followupDue": c.decision.followup_due.isoformat() if c.decision else None, "followupDone": bool(c.followup),
                   "reflected": bool(c.reflection), "createdAt": c.created_at.isoformat()} for c in cases],
        "followups": [{"caseId": c.id, "title": packs.case_title(c.situation_id, c.inputs), "due": c.decision.followup_due.isoformat(),
                       "overdue": c.decision.followup_due.isoformat() <= today} for c in decided if not c.followup],
        "stats": {
            "started": len(cases),
            "decided": len(decided),
            "exported": len({e.case_id for e in entries if e.type == "export"}),
            "followedUp": sum(1 for c in decided if c.followup),
            "reportedWorked": sum(1 for c in decided if c.followup and c.followup.outcome in ("worked", "partly")),
            "confidenceChange": round(sum(c.reflection.confidence_after - c.confidence_before for c in reflected) / len(reflected), 1) if reflected else None,
        },
    }


@router.get("/reminders")
def reminder_badge(user=Depends(current_user), r=Depends(get_redis)):
    return {"due": reminders.due_count(r, user.id)}


@router.get("/documents")
def library(user=Depends(current_user), db: Session = Depends(get_db)):
    """Everything the user has created, newest first."""
    docs = db.scalars(select(Document).where(Document.user_id == user.id).order_by(Document.updated_at.desc())).all()
    cases = {c.id: c for c in db.scalars(select(Case).where(Case.user_id == user.id))}
    titles = {i: packs.case_title(c.situation_id, c.inputs) for i, c in cases.items()}
    return {"documents": [{"id": d.id, "caseId": d.case_id, "kind": d.kind, "label": doc_label(cases[d.case_id].situation_id, d.kind), "caseTitle": titles.get(d.case_id, ""),
                           "body": d.body, "revisions": len(d.revisions), "createdAt": d.created_at.isoformat(), "updatedAt": d.updated_at.isoformat()} for d in docs]}
