import json
import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, object_session

from .. import billing, llm, packs, presets, reminders
from ..cache import get_redis
from ..db import get_db
from ..deps import current_user, own_case
from ..document import build_debrief, build_document
from ..documents import KINDS, MAX_LEN, get_doc, save_document
from .. import engine
from ..errors import ApiError
from ..msg import tr
from ..models import Case, Decision, FollowUp, JournalEntry, Profile, Reflection
from ..security import sha
from ..validate import validate_answers

router = APIRouter(prefix="/api")

OUTCOMES = {"worked": "It worked", "partly": "Partly worked", "not_yet": "Not resolved yet", "not_applied": "I did not use it at work"}


def sit_of(c: Case) -> dict:
    return presets.resolve(object_session(c), c.user_id, c.situation_id)


def case_dict(c: Case) -> dict:
    d, rf, fu = c.decision, c.reflection, c.followup
    out = {
        "id": c.id, "situationId": c.situation_id, "title": packs.case_title(c.situation_id, c.inputs), "inputs": c.inputs, "result": c.result,
        "confidenceBefore": c.confidence_before, "status": c.status,
        "chosenOption": d.option if d else None, "rationale": d.rationale if d else None,
        "document": d.document if d else None, "decidedAt": d.decided_at.isoformat() if d else None,
        "followupDue": d.followup_due.isoformat() if d else None,
        "reflection": {"learned": rf.learned, "different": rf.different, "confidenceAfter": rf.confidence_after} if rf else None,
        "followup": {"outcome": fu.outcome, "notes": fu.notes} if fu else None,
        "createdAt": c.created_at.isoformat(),
    }
    if d:
        cr, cm = get_doc(c, "change_request"), get_doc(c, "client_message")
        out["document"] = cr.body if cr else d.document
        out["documentUpdatedAt"] = cr.updated_at.isoformat() if cr else None
        out["documentRevisions"] = len(cr.revisions) if cr else 0
        out["clientMessage"] = cm.body if cm else None
        out["debrief"] = build_debrief(c.result, d.option, c.inputs, c.situation_id, sit_of(c))
    return out


def confidence(v):
    return v if isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 5 else None


def calc(sit: dict, raw_inputs):
    values, errors = validate_answers(sit["questions"], raw_inputs)
    if not errors:
        errors = engine.check(sit, values)
    if errors:
        raise ApiError(400, "Check the highlighted fields", errors)
    inputs = {**values, "asOf": packs.today()}
    return inputs, engine.run(sit, inputs)


def log(db, uid, case_id, type_, text):
    db.add(JournalEntry(user_id=uid, case_id=case_id, type=type_, text=text))


@router.post("/cases", status_code=201)
def create_case(body: dict, user=Depends(current_user), db: Session = Depends(get_db)):
    sit = presets.resolve(db, user.id, body.get("situationId"))
    if not sit:
        raise ApiError(400, "Unknown situation")
    if not billing.can_start_case(db, user.id):
        raise ApiError(402, "You have used your free situations. Get the pass to start more. Your saved cases stay available.")
    if body.get("privacyAck") is not True:
        raise ApiError(400, "Confirm that you did not enter confidential employer or client information")
    conf = confidence(body.get("confidenceBefore"))
    if not conf:
        raise ApiError(400, "Rate your confidence from 1 to 5")
    inputs, result = calc(sit, body.get("inputs"))
    c = Case(user_id=user.id, situation_id=sit["id"], inputs=inputs, result=result, confidence_before=conf)
    db.add(c)
    db.flush()
    log(db, user.id, c.id, "case", tr("Started: {title}", title=packs.case_title(sit['id'], inputs)))
    db.commit()
    return {"case": case_dict(c)}


@router.get("/cases/{case_id}")
def get_case(c: Case = Depends(own_case)):
    return {"case": case_dict(c)}


@router.put("/cases/{case_id}/inputs")
def recalc(body: dict, c: Case = Depends(own_case), db: Session = Depends(get_db)):
    if c.status != "draft":
        raise ApiError(409, "This case already has a decision")
    c.inputs, c.result = calc(sit_of(c), body.get("inputs"))
    db.commit()
    return {"case": case_dict(c)}


@router.post("/cases/{case_id}/decision")
def decide(body: dict, c: Case = Depends(own_case), user=Depends(current_user), db: Session = Depends(get_db), r=Depends(get_redis)):
    if c.status != "draft":
        raise ApiError(409, "This case already has a decision")
    sit = sit_of(c)
    option = str(body.get("option") or "")
    if option not in sit["options"]:
        raise ApiError(400, "Choose an option")
    rationale = str(body.get("rationale") or "").strip()[:600]
    days = body.get("followupDays")
    days = days if isinstance(days, int) and not isinstance(days, bool) and 1 <= days <= 30 else 3
    profile = db.get(Profile, user.id)
    due = date.fromisoformat(packs.add_days(packs.today(), days))
    c.decision = Decision(
        option=option, rationale=rationale, followup_due=due, decided_at=datetime.now(timezone.utc),
        document=build_document(c.inputs, c.result, option, rationale, profile and packs.get_role(profile.role_id), user.email, packs.today(), sit["id"], sit),
    )
    c.status = "decided"
    save_document(db, c, "change_request", c.decision.document, source="generated")
    log(db, user.id, c.id, "decision", tr("Decided: {option}. {title}", option=sit['options'][option]['label'], title=packs.case_title(c.situation_id, c.inputs)))
    db.commit()
    reminders.schedule(r, user.id, c.id, due.isoformat())
    return {"case": case_dict(c)}


@router.post("/cases/{case_id}/reflection")
def reflect(body: dict, c: Case = Depends(own_case), user=Depends(current_user), db: Session = Depends(get_db)):
    if c.status != "decided":
        raise ApiError(409, "Make a decision first")
    after = confidence(body.get("confidenceAfter"))
    if not after:
        raise ApiError(400, "Rate your confidence from 1 to 5")
    refl = {"learned": str(body.get("learned") or "").strip()[:600], "different": str(body.get("different") or "").strip()[:600], "confidenceAfter": after}
    c.reflection = Reflection(learned=refl["learned"], different=refl["different"], confidence_after=after)
    log(db, user.id, c.id, "reflection", tr("Reflection: confidence {before} -> {after}.", before=c.confidence_before, after=after) + (f" {refl['learned']}" if refl["learned"] else ""))
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
    c.followup = FollowUp(outcome=outcome, notes=notes)
    log(db, user.id, c.id, "followup", tr("Follow-up (as you reported): {outcome}.", outcome=tr(OUTCOMES[outcome])) + (f" {notes}" if notes else ""))
    db.commit()
    reminders.clear(r, user.id, c.id)
    return {"case": case_dict(c)}


@router.post("/cases/{case_id}/hint")
def hint(c: Case = Depends(own_case), db: Session = Depends(get_db), r=Depends(get_redis)):
    if not llm.enabled():
        raise ApiError(404, "AI suggestions are not configured")
    if c.status != "decided":
        raise ApiError(409, "Make a decision first")
    sit = sit_of(c)
    if sit["engine"] != "change_request":
        raise ApiError(409, "AI drafts are available for client change requests only")
    opt = next(o for o in c.result["options"] if o["key"] == c.decision.option)
    args = (c.inputs["changeTitle"], sit["options"][c.decision.option]["label"], opt["newReleaseDate"], opt["extraCost"], c.decision.rationale)
    key = "hint:" + sha(json.dumps(args))
    text = r.get(key)
    if text is None:
        try:
            text = llm.client_message_hint(*args)
        except llm.LlmError as e:  # network, quota, bad key: the document is unaffected
            logging.getLogger("roleshift.llm").warning("hint failed case=%s reason=%s", c.id, e)
            raise ApiError(502, "AI suggestion is unavailable right now. Your document is not affected.")
        r.set(key, text, ex=86400)
    save_document(db, c, "client_message", text, source="ai")  # kept in Postgres: the Redis cache expires
    db.commit()
    return {"text": text}


@router.put("/cases/{case_id}/documents/{kind}")
def save_doc(kind: str, body: dict, c: Case = Depends(own_case), db: Session = Depends(get_db)):
    if kind not in KINDS:
        raise ApiError(404, "Unknown document")
    if c.status != "decided":
        raise ApiError(409, "Make a decision first")
    text = body.get("body")
    if not isinstance(text, str) or not text.strip():
        raise ApiError(400, "The document cannot be empty")
    if len(text) > MAX_LEN:
        raise ApiError(400, tr("The document is too long (max {n} characters)", n=MAX_LEN))
    save_document(db, c, kind, text.replace("\r\n", "\n"), source="user")
    db.commit()
    return {"case": case_dict(c)}


@router.get("/cases/{case_id}/documents/{kind}/revisions")
def revisions(kind: str, c: Case = Depends(own_case)):
    doc = get_doc(c, kind)
    if not doc:
        raise ApiError(404, "Not found")
    return {"revisions": [{"id": r.id, "source": r.source, "createdAt": r.created_at.isoformat(), "body": r.body} for r in reversed(doc.revisions)]}


@router.post("/cases/{case_id}/export")
def record_export(body: dict, c: Case = Depends(own_case), db: Session = Depends(get_db)):
    """The user copied or downloaded the document: a weak but objective sign they mean to use it."""
    how = body.get("how")
    if how not in ("copy", "download"):
        raise ApiError(400, "Unknown export type")
    if c.status != "decided":
        raise ApiError(409, "Make a decision first")
    log(db, c.user_id, c.id, "export", tr("Exported the document ({how}): {title}", how=tr("copied") if how == "copy" else tr("downloaded"), title=packs.case_title(c.situation_id, c.inputs)))
    db.commit()
    return {"ok": True}
