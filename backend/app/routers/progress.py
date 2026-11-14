"""The user's own progress (read-only aggregation of existing tables) and the email reminder controls.
The one-click links from emails (outcome, unsubscribe) are public GET pages: they work without signing in."""
import asyncio
import hmac
import html
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config, emails, mailer, packs, prediction, presets
from ..cache import get_redis
from ..db import SessionLocal, get_db
from ..deps import current_user
from ..errors import ApiError
from ..msg import tr
from ..models import Case, Document, JournalEntry, Profile
from .cases import OUTCOMES

router = APIRouter(prefix="/api")
log = logging.getLogger("roleshift.progress")
SKILLS = {"prioritising": "Prioritising under pressure", "estimating": "Estimating and promising dates", "choosing": "Choosing between options", "changes": "Handling late changes"}
STATUS = {"draft": "In progress", "decided": "Decided", "due": "Follow-up due", "done": "Outcome recorded"}


def _day(dt) -> str:
    return dt.date().isoformat()


@router.get("/progress")
def progress(user=Depends(current_user), db: Session = Depends(get_db)):
    profile = db.get(Profile, user.id)
    cases = db.scalars(select(Case).where(Case.user_id == user.id).order_by(Case.id.desc())).all()
    today = packs.today()
    now = datetime.now(timezone.utc)
    sits = {sid: presets.resolve(db, user.id, sid) for sid in {c.situation_id for c in cases}}
    start = user.created_at
    day = (now.date() - start.date()).days + 1

    decided = [c for c in cases if c.status == "decided"]
    confidence = [{"caseId": c.id, "title": packs.case_title(c.situation_id, c.inputs), "date": _day(c.created_at), "before": c.confidence_before,
                   "after": c.reflection.confidence_after if c.reflection else None} for c in reversed(decided)]
    changes = [x["after"] - x["before"] for x in confidence if x["after"] is not None]

    timeline = []
    for c in cases:
        sit = sits.get(c.situation_id) or {}
        status = "draft" if c.status == "draft" else "done" if c.followup else "due" if c.decision.followup_due.isoformat() <= today else "decided"
        timeline.append({
            "caseId": c.id, "date": _day(c.created_at), "title": packs.case_title(c.situation_id, c.inputs), "situation": sit.get("title", ""),
            "category": sit.get("category") or "Other", "chosen": (sit.get("options", {}).get(c.decision.option, {}).get("label") if c.decision else None),
            "status": status, "statusLabel": tr(STATUS[status]), "outcome": c.followup.outcome if c.followup else None,
            "outcomeLabel": tr(OUTCOMES[c.followup.outcome]) if c.followup else None,
            "guess": ({"hits": sum(p["hit"] for p in c.prediction_score["parts"]), "parts": len(c.prediction_score["parts"]), "overall": c.prediction_score["overall"]}
                      if c.prediction_score else None)})

    practiced: dict = {}
    for c in cases:
        sit = sits.get(c.situation_id) or {}
        cat = practiced.setdefault(sit.get("category") or "Other", {})
        cat[sit.get("title", c.situation_id)] = cat.get(sit.get("title", c.situation_id), 0) + 1

    # skills: how often the guess made before the numbers agreed with the calculator (never a trend from fewer than 3 guesses)
    skills = []
    for key, label in SKILLS.items():
        mine = [c for c in reversed(cases) if (sits.get(c.situation_id) or {}).get("skill") == key]
        guesses = [c.prediction_score["overall"] for c in mine if c.prediction_score]
        enough = len(guesses) >= prediction.MIN_FOR_TREND
        skills.append({"key": key, "label": tr(label), "cases": len(mine), "guesses": len(guesses), "enough": enough,
                       "hitRate": round(100 * sum(guesses[-10:]) / len(guesses[-10:])) if enough else None,
                       "ticks": guesses[-10:] if enough else []})
    outcomes = {k: sum(1 for c in decided if c.followup and c.followup.outcome == k) for k in OUTCOMES}
    entries = db.scalars(select(JournalEntry).where(JournalEntry.user_id == user.id)).all()
    last = max([c.created_at for c in cases] + [e.created_at for e in entries], default=None)
    inactive = (now.date() - last.date()).days if last else None
    tried = {c.situation_id for c in cases}
    role = profile.role_id if profile else None
    nxt = next((s for s in packs.situations if ("*" in s["applies_to"] or role in s["applies_to"]) and s["id"] not in tried), None)
    firsts = lambda xs: min(xs).date().isoformat() if xs else None
    return {
        "startedAt": _day(start), "day": day, "windowDays": 90, "inWindow": day <= 90, "milestones": [30, 60, 90],
        "confidence": confidence, "averageChange": round(sum(changes) / len(changes), 1) if changes else None,
        "timeline": timeline,
        "counts": {"situations": len(cases), "decisions": len(decided), "followups": sum(1 for c in decided if c.followup),
                   "documents": db.query(Document).filter(Document.user_id == user.id).count(),
                   "exported": len({e.case_id for e in entries if e.type == "export"})},
        "practiced": [{"category": k, "situations": [{"title": t, "count": n} for t, n in v.items()]} for k, v in practiced.items()],
        "skills": skills, "minForTrend": prediction.MIN_FOR_TREND,
        "outcomes": outcomes, "outcomesTotal": sum(outcomes.values()),
        "firsts": {"situation": firsts([c.created_at for c in cases]), "decision": firsts([c.decision.decided_at for c in decided]),
                   "debrief": firsts([c.reflection.created_at for c in decided if c.reflection])},
        "inactiveDays": inactive, "inactiveHint": inactive is not None and inactive >= 7,
        "tryNext": {"id": nxt["id"], "title": nxt["title"], "summary": nxt["summary"]} if nxt else None,
        "emailReminders": bool(profile and profile.email_reminders), "logMailer": mailer.is_log_mailer(),
    }


@router.post("/progress/reminders")
def set_reminders(body: dict, user=Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(Profile, user.id)
    if not p:
        raise ApiError(409, "Set up your profile first")
    if not isinstance(body.get("enabled"), bool):
        raise ApiError(400, "Choose on or off")
    p.email_reminders = body["enabled"]
    db.commit()
    return {"emailReminders": p.email_reminders}


@router.post("/progress/send-reminders-now")
def send_now(user=Depends(current_user), db: Session = Depends(get_db), r=Depends(get_redis)):
    """Development helper: sends this user's due reminders right away. Only with the log mailer or TEST_CHECKOUT on."""
    if not (mailer.is_log_mailer() or config.TEST_CHECKOUT):
        raise ApiError(404, "Not available")
    p = db.get(Profile, user.id)
    if not p or not p.email_reminders:
        raise ApiError(409, "Turn on email reminders first")
    return {"sent": emails.send_due_followups(db, r, only_user=user.id), "logMailer": mailer.is_log_mailer()}


def _page(title: str, text: str, redirect: str | None = None) -> HTMLResponse:
    meta = f'<meta http-equiv="refresh" content="3;url={html.escape(redirect)}">' if redirect else ""
    link = f'<p><a href="{html.escape(redirect)}">Continue</a></p>' if redirect else ""
    return HTMLResponse(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{meta}'
                        f'<title>{html.escape(title)}</title><style>body{{font:18px/1.5 system-ui;max-width:32rem;margin:15vh auto;padding:0 16px}}</style></head>'
                        f'<body><h1>{html.escape(title)}</h1><p>{html.escape(text)}</p>{link}</body></html>')


@router.get("/followup/{token}")
def email_outcome(token: str, db: Session = Depends(get_db), r=Depends(get_redis)):
    case = emails.record_outcome(db, r, token)
    if not case:
        raise ApiError(404, "This link is not valid any more")
    return _page(tr("Thanks, saved"), tr("Your answer is in your journal. You can add details on the case page."), f"{config.APP_URL}/case/{case.id}")


@router.get("/unsubscribe/{token}")
def email_unsubscribe(token: str, db: Session = Depends(get_db)):
    if not emails.unsubscribe(db, token):
        raise ApiError(404, "This link is not valid any more")
    return _page(tr("Reminders are off"), tr("We will not email you any more reminders. You can turn them on again in the app."))


@router.get("/internal/cron/followups")
def cron_followups(request: Request, db: Session = Depends(get_db)):
    """Daily job on Vercel (the background loop does not run there). Protected by CRON_SECRET; off when it is not set."""
    secret = config.CRON_SECRET
    if not secret or not hmac.compare_digest(request.headers.get("authorization", ""), f"Bearer {secret}"):
        raise ApiError(404, "Not found")
    res = emails.run_all(db, get_redis())
    log.info("cron reminders %s", res)
    return {"ok": True, **res}


async def reminder_loop():
    """Every 10 minutes; a Redis lock keeps two workers from sending the same email twice."""
    r = get_redis()
    while True:
        try:
            if r.set("lock:reminders", "1", nx=True, ex=540):
                def work():
                    with SessionLocal() as db:
                        return emails.run_all(db, r)
                res = await asyncio.to_thread(work)
                if any(res.values()):
                    log.info("reminders sent %s", res)
        except Exception as e:
            log.warning("reminder run failed: %s", type(e).__name__)
        await asyncio.sleep(600)
