"""Demo account: a throwaway user pre-loaded with every step of the flow, so a reviewer can see
the whole product in one click without signing up."""
import secrets
from datetime import date, datetime, timedelta, timezone

from . import packs, reminders
from .document import build_document
from .documents import save_document
from . import engine
from .engine.change_request import compute
from .models import Case, Decision, FollowUp, JournalEntry, Profile, Reflection, User
from .security import hash_password
from .validate import validate_answers

DEMO_DOMAIN = "demo.roleshift.local"

BASE = dict(
    requestedBy="Jordan, VP Operations (client)", teamSize=6, dailyRate=600, budgetRemaining=40000,
    bufferDays=2, clientCoversPct=0, delayPenaltyPerDay=0, overheadPct=25, parallelPct=60, focusPct=70,
)


def is_demo_email(email: str) -> bool:
    return email.endswith("@" + DEMO_DOMAIN)


def _answers(**over) -> dict:
    sit = packs.get_situation("client-change-request")
    release = packs.next_weekday(packs.add_days(packs.today(), 14))
    values, errors = validate_answers(sit["questions"], {**BASE, "releaseDate": release, **over})
    assert not errors, errors
    return {**values, "asOf": packs.today()}


def _case(db, user, ago_days: int, confidence: int, **answers) -> Case:
    inputs = _answers(**answers)
    c = Case(user_id=user.id, situation_id="client-change-request", inputs=inputs, result=compute(inputs),
             confidence_before=confidence, created_at=datetime.now(timezone.utc) - timedelta(days=ago_days))
    db.add(c)
    db.flush()
    db.add(JournalEntry(user_id=user.id, case_id=c.id, type="case", text=f"Started: {inputs['changeTitle']}",
                        created_at=c.created_at))
    return c


def _decide(db, user, c: Case, option: str, rationale: str, followup_days: int, role, ago_days: int):
    sit = packs.get_situation(c.situation_id)
    decided_at = datetime.now(timezone.utc) - timedelta(days=ago_days)
    c.decision = Decision(
        option=option, rationale=rationale, decided_at=decided_at,
        followup_due=date.fromisoformat(packs.add_days(packs.today(), followup_days)),
        document=build_document(c.inputs, c.result, option, rationale, role, user.email, packs.today()),
    )
    c.status = "decided"
    save_document(db, c, "change_request", c.decision.document, source="generated")
    db.add(JournalEntry(user_id=user.id, case_id=c.id, type="decision", created_at=decided_at,
                        text=f"Decided: {sit['options'][option]['label']}. {c.inputs['changeTitle']}"))


def seed_demo_user(db, r) -> User:
    user = User(email=f"demo-{secrets.token_hex(4)}@{DEMO_DOMAIN}", password_hash=hash_password(secrets.token_hex(16)))
    db.add(user)
    db.flush()
    role = packs.get_role("it-pm")
    db.add(Profile(user_id=user.id, role_id="it-pm", industry="Fintech", tenure="1-3m",
                   fears=["wrong-call", "pushback"], fear_note=""))
    db.add(JournalEntry(user_id=user.id, type="onboarding", text="Set up profile as IT Project Manager in Fintech.",
                        created_at=datetime.now(timezone.utc) - timedelta(days=8)))

    # 1. A finished case: decision, document, reflection and a reported outcome.
    a = _case(db, user, 7, 2, changeTitle="Add CSV export to the reports screen", priority="important",
              changeDescription="Client wants a CSV export of the monthly report. Acceptance: all columns, UTF-8.",
              changeEffortDays=4, bufferDays=5, clientCoversPct=100)
    _decide(db, user, a, "accept", "Small effort, fits the buffer, and the client pays for it.", 3, role, 7)
    save_document(db, a, "change_request", a.decision.document + "\n\nNote: client confirmed the CSV columns by email.", source="user", journal=False)
    save_document(db, a, "client_message", "Hi [Name], we can include the CSV export in this release. It fits our schedule buffer and you cover the cost, "
                  "so the release date stays the same. Please sign the attached Change Request.", source="user", journal=False)
    a.reflection = Reflection(learned="Getting an estimate from the team before answering made the call easy.",
                              different="Ask about acceptance criteria in the first conversation.", confidence_after=4)
    a.followup = FollowUp(outcome="worked", notes="Client signed the Change Request the same day.")
    db.add(JournalEntry(user_id=user.id, case_id=a.id, type="reflection", text="Reflection: confidence 2 -> 4. " + a.reflection.learned,
                        created_at=datetime.now(timezone.utc) - timedelta(days=6)))
    db.add(JournalEntry(user_id=user.id, case_id=a.id, type="followup", text="Follow-up (as you reported): It worked. " + a.followup.notes,
                        created_at=datetime.now(timezone.utc) - timedelta(days=4)))

    # 2. Decided, waiting for reflection and a follow-up that is due today.
    b = _case(db, user, 2, 3, changeTitle="Switch to the new payment webhook format", priority="must",
              changeDescription="Payment provider retires the old webhook on the release date.",
              changeEffortDays=12, bufferDays=2, delayPenaltyPerDay=500)
    _decide(db, user, b, "accept", "Must-have: the provider shuts down the old format. Escalating the budget gap.", 0, role, 2)

    # 3. A draft with numbers entered: the user picks an option and decides.
    _case(db, user, 0, 3, changeTitle="Add dark mode to the dashboard", priority="nice", changeEffortDays=8)

    # 4. Competing priorities from a storyline, ready to compare (the newcomer situation, not client work).
    sit = packs.public_pack_situation("competing-priorities")
    story = sit["storylines"][0]["answers"]
    values, errors = validate_answers(sit["questions"], story)
    assert not errors, errors
    inputs = {**values, "asOf": packs.today()}
    p = Case(user_id=user.id, situation_id=sit["id"], inputs=inputs, result=engine.run(sit, inputs), confidence_before=2)
    db.add(p)
    db.flush()
    db.add(JournalEntry(user_id=user.id, case_id=p.id, type="case", text=f"Started: {inputs['title']}"))

    db.commit()
    reminders.schedule(r, user.id, b.id, b.decision.followup_due.isoformat())
    return user
