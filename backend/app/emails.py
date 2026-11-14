"""Opt-in reminder emails: "how did it go?" for a decision whose follow-up date has come, and one nudge on day 7.
Only users who turned reminders on, never demo users, each email at most once. One-click links record an outcome or
unsubscribe; tokens are random, stored hashed, expire after 30 days (outcome links are single use)."""
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import config, mailer, packs, reminders
from .demo import is_demo_email
from .models import Case, Decision, EmailToken, FollowUp, JournalEntry, Profile, User
from .security import sha

log = logging.getLogger("roleshift.emails")
TOKEN_DAYS = 30
OUTCOME_LINKS = [("worked", "It worked"), ("partly", "Partly"), ("not_yet", "It did not work yet")]


def make_token(db: Session, user_id: int, case_id: int | None, kind: str, days: int = TOKEN_DAYS) -> str:
    raw = secrets.token_urlsafe(24)
    db.add(EmailToken(user_id=user_id, case_id=case_id, kind=kind, token_hash=sha(raw), expires_at=datetime.now(timezone.utc) + timedelta(days=days)))
    return raw


def _footer(db: Session, user_id: int) -> str:
    return f"\n--\nYou get this because you turned on reminders in RoleShift.\nTurn them off: {config.APP_URL}/api/unsubscribe/{make_token(db, user_id, None, 'unsubscribe', 365)}\n"


def followup_email(db: Session, user: User, case: Case) -> tuple[str, str]:
    title = packs.case_title(case.situation_id, case.inputs)
    links = "\n".join(f"  {label}: {config.APP_URL}/api/followup/{make_token(db, user.id, case.id, kind)}" for kind, label in OUTCOME_LINKS)
    body = (f"How did it go with \"{title}\"?\n\nYou decided on {case.decision.decided_at.date().isoformat()} and asked us to check back. "
            f"One click records what happened (it is what you tell us, nothing is checked):\n{links}\n\n"
            f"Or open the case and write more: {config.APP_URL}/case/{case.id}\n" + _footer(db, user.id))
    return f"How did it go with {title}?", body


def day7_email(db: Session, user: User) -> tuple[str, str]:
    body = (f"A week ago you started with RoleShift. A small step helps most: pick the next scenario you expect at work "
            f"and rehearse it with your own numbers.\n\nPick your next scenario: {config.APP_URL}/\n" + _footer(db, user.id))
    return "Pick your next scenario", body


def _eligible(db: Session):
    return (Profile.email_reminders.is_(True),)


def send_due_followups(db: Session, r, now: datetime | None = None, only_user: int | None = None) -> int:
    """One email per due follow-up of an opted-in, non-demo user whose reminder was not sent yet. Returns how many."""
    now = now or datetime.now(timezone.utc)
    q = (select(Case, User).join(User, User.id == Case.user_id).join(Profile, Profile.user_id == User.id).join(Decision, Decision.case_id == Case.id)
         .where(Profile.email_reminders.is_(True), Case.status == "decided", Decision.reminder_sent_at.is_(None),
                Decision.followup_due <= now.date(), ~Case.id.in_(select(FollowUp.case_id))))
    if only_user is not None:
        q = q.where(User.id == only_user)
    sent = 0
    for case, user in db.execute(q).all():
        if is_demo_email(user.email):
            continue
        subject, body = followup_email(db, user, case)
        try:
            mailer.send(r, user.email, subject, body)
        except Exception as e:  # SMTP down: leave it unsent, the next run retries
            db.rollback()
            log.warning("followup email failed user=%s case=%s reason=%s", user.id, case.id, type(e).__name__)
            continue
        case.decision.reminder_sent_at = now
        db.commit()
        sent += 1
        log.info("followup email sent user=%s case=%s", user.id, case.id)
    return sent


def send_day7_nudges(db: Session, r, now: datetime | None = None, only_user: int | None = None) -> int:
    """Once, to opted-in users 7+ days after signup who started fewer than 2 scenarios of their own."""
    now = now or datetime.now(timezone.utc)
    q = (select(User).join(Profile, Profile.user_id == User.id)
         .where(Profile.email_reminders.is_(True), Profile.day7_nudge_sent_at.is_(None), User.created_at <= now - timedelta(days=7)))
    if only_user is not None:
        q = q.where(User.id == only_user)
    sent = 0
    for user in db.scalars(q).all():
        if is_demo_email(user.email):
            continue
        cases = db.scalar(select(func.count()).select_from(Case).where(Case.user_id == user.id, Case.seeded.is_(False))) or 0
        if cases >= 2:
            continue
        subject, body = day7_email(db, user)
        try:
            mailer.send(r, user.email, subject, body)
        except Exception as e:
            db.rollback()
            log.warning("day7 email failed user=%s reason=%s", user.id, type(e).__name__)
            continue
        db.get(Profile, user.id).day7_nudge_sent_at = now
        db.commit()
        sent += 1
        log.info("day7 email sent user=%s", user.id)
    return sent


def run_all(db: Session, r, now: datetime | None = None) -> dict:
    return {"followups": send_due_followups(db, r, now), "day7": send_day7_nudges(db, r, now)}


def _valid(db: Session, raw: str, kinds: tuple, reusable: bool = False) -> EmailToken | None:
    t = db.scalar(select(EmailToken).where(EmailToken.token_hash == sha(raw)))
    if not t or t.kind not in kinds or t.expires_at < datetime.now(timezone.utc) or (t.used_at and not reusable):
        return None
    return t


def record_outcome(db: Session, r, raw: str) -> Case | None:
    """The one-click outcome link. Single use; the other outcome links of the same case stop working too."""
    t = _valid(db, raw, ("worked", "partly", "not_yet"))
    if not t or t.case_id is None:
        return None
    case = db.get(Case, t.case_id)
    if not case or case.user_id != t.user_id or case.status != "decided":
        return None
    now = datetime.now(timezone.utc)
    if not case.followup:
        case.followup = FollowUp(outcome=t.kind, notes="")
        label = {"worked": "It worked", "partly": "Partly worked", "not_yet": "Not resolved yet"}[t.kind]
        db.add(JournalEntry(user_id=case.user_id, case_id=case.id, type="followup", text=f"Follow-up from the email link (as you reported): {label}."))
        reminders.clear(r, case.user_id, case.id)
    for other in db.scalars(select(EmailToken).where(EmailToken.case_id == case.id, EmailToken.kind.in_(["worked", "partly", "not_yet"]))):
        other.used_at = other.used_at or now
    db.commit()
    return case


def unsubscribe(db: Session, raw: str) -> bool:
    t = _valid(db, raw, ("unsubscribe",), reusable=True)
    if not t:
        return False
    p = db.get(Profile, t.user_id)
    if p:
        p.email_reminders = False
    t.used_at = datetime.now(timezone.utc)
    db.commit()
    return True
