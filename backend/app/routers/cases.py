import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import llm, packs, reminders
from ..cache import get_redis
from ..db import get_db
from ..deps import current_user, own_case
from ..document import build_debrief, build_document
from ..engine.change_request import compute
from ..errors import ApiError
from ..models import Case, JournalEntry, Profile
from ..security import sha
from ..validate import validate_answers

router = APIRouter(prefix="/api")

OUTCOMES = {"worked": "It worked", "partly": "Partly worked", "not_yet": "Not resolved yet", "not_applied": "I did not use it at work"}


def case_dict(c: Case) -> dict:
    out = {
        "id": c.id, "situationId": c.situation_id, "inputs": c.inputs, "result": c.result,
        "confidenceBefore": c.confidence_before, "status": c.status, "chosenOption": c.chosen_option,
        "rationale": c.rationale, "document": c.document,
        "decidedAt": c.decided_at.isoformat() if c.decided_at else None,
        "followupDue": c.followup_due, "reflection": c.reflection, "followup": c.followup,
        "createdAt": c.created_at.isoformat(),
    }
    if c.status == "decided":
        out["debrief"] = build_debrief(c.result, c.chosen_option, c.inputs)
    return out


def confidence(v):
    return v if isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 5 else None


def calc(sit: dict, raw_inputs):
    values, errors = validate_answers(sit["questions"], raw_inputs)
    if errors:
        raise ApiError(400, "Check the highlighted fields", errors)
    inputs = {**values, "asOf": packs.today()}
    return inputs, compute(inputs)


def log(db, uid, case_id, type_, text):
    db.add(JournalEntry(user_id=uid, case_id=case_id, type=type_, text=text))


@router.post("/cases", status_code=201)
def create_case(body: dict, user=Depends(current_user), db: Session = Depends(get_db)):
    sit = packs.get_situation(body.get("situationId"))
    if not sit:
        raise ApiError(400, "Unknown situation")
    conf = confidence(body.get("confidenceBefore"))
    if not conf:
        raise ApiError(400, "Rate your confidence from 1 to 5")
    inputs, result = calc(sit, body.get("inputs"))
    c = Case(user_id=user.id, situation_id=sit["id"], inputs=inputs, result=result, confidence_before=conf)
    db.add(c)
    db.flush()
    log(db, user.id, c.id, "case", f"Started: {inputs['changeTitle']}")
    db.commit()
    return {"case": case_dict(c)}


@router.get("/cases/{case_id}")
def get_case(c: Case = Depends(own_case)):
    return {"case": case_dict(c)}


@router.put("/cases/{case_id}/inputs")
def recalc(body: dict, c: Case = Depends(own_case), db: Session = Depends(get_db)):
    if c.status != "draft":
        raise ApiError(409, "This case already has a decision")
    c.inputs, c.result = calc(packs.get_situation(c.situation_id), body.get("inputs"))
    db.commit()
    return {"case": case_dict(c)}


@router.post("/cases/{case_id}/decision")
def decide(body: dict, c: Case = Depends(own_case), user=Depends(current_user), db: Session = Depends(get_db), r=Depends(get_redis)):
    if c.status != "draft":
        raise ApiError(409, "This case already has a decision")
    sit = packs.get_situation(c.situation_id)
    option = str(body.get("option") or "")
    if option not in sit["options"]:
        raise ApiError(400, "Choose an option")
    rationale = str(body.get("rationale") or "").strip()[:600]
    days = body.get("followupDays")
    days = days if isinstance(days, int) and not isinstance(days, bool) and 1 <= days <= 30 else 3
    profile = db.get(Profile, user.id)
    c.document = build_document(c.inputs, c.result, option, rationale, profile and packs.get_role(profile.role_id), user.email, packs.today())
    c.status, c.chosen_option, c.rationale = "decided", option, rationale
    c.decided_at = datetime.now(timezone.utc)
    c.followup_due = packs.add_days(packs.today(), days)
    log(db, user.id, c.id, "decision", f"Decided: {sit['options'][option]['label']}. {c.inputs['changeTitle']}")
    db.commit()
    reminders.schedule(r, user.id, c.id, c.followup_due)
    return {"case": case_dict(c)}


@router.post("/cases/{case_id}/reflection")
def reflect(body: dict, c: Case = Depends(own_case), user=Depends(current_user), db: Session = Depends(get_db)):
    if c.status != "decided":
        raise ApiError(409, "Make a decision first")
    after = confidence(body.get("confidenceAfter"))
    if not after:
        raise ApiError(400, "Rate your confidence from 1 to 5")
    refl = {"learned": str(body.get("learned") or "").strip()[:600], "different": str(body.get("different") or "").strip()[:600], "confidenceAfter": after}
    c.reflection = refl
    log(db, user.id, c.id, "reflection", f"Reflection: confidence {c.confidence_before} -> {after}." + (f" {refl['learned']}" if refl["learned"] else ""))
    db.commit()
    return {"case": case_dict(c)}


@router.post("/cases/{case_id}/followup")
def followup(body: dict, c: Case = Depends(own_case), user=Depends(current_user), db: Session = Depends(get_db), r=Depends(get_redis)):
    if c.status != "decided":
        raise ApiError(409, "Make a decision first")
    outcome = str(body.get("outcome") or "")
    if outcome not in OUTCOMES:
        raise ApiError(400, "Choose what happened")
    notes = str(body.get("notes") or "").strip()[:800]
    c.followup = {"outcome": outcome, "notes": notes, "at": datetime.now(timezone.utc).isoformat()}
    log(db, user.id, c.id, "followup", f"Follow-up (as you reported): {OUTCOMES[outcome]}." + (f" {notes}" if notes else ""))
    db.commit()
    reminders.clear(r, user.id, c.id)
    return {"case": case_dict(c)}


@router.post("/cases/{case_id}/hint")
def hint(c: Case = Depends(own_case), r=Depends(get_redis)):
    if not llm.enabled():
        raise ApiError(404, "AI suggestions are not configured")
    if c.status != "decided":
        raise ApiError(409, "Make a decision first")
    sit = packs.get_situation(c.situation_id)
    opt = next(o for o in c.result["options"] if o["key"] == c.chosen_option)
    args = (c.inputs["changeTitle"], sit["options"][c.chosen_option]["label"], opt["newReleaseDate"], opt["extraCost"], c.rationale)
    key = "hint:" + sha(json.dumps(args))
    text = r.get(key)
    if text is None:
        try:
            text = llm.client_message_hint(*args)
        except Exception as e:  # network, quota, bad key: the document is unaffected
            print("LLM error:", type(e).__name__)
            raise ApiError(502, "AI suggestion is unavailable right now. Your document is not affected.")
        r.set(key, text, ex=86400)
    return {"text": text}
