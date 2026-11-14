"""What a user may do on their plan. Free: FREE_CASES situations of their own. Pass: everything for PASS_DAYS."""
from .msg import tr
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import config
from .models import Case, Purchase

PLAN = "pass90"


def plans() -> dict:
    return {
        "free": {"name": tr('Free'), "priceCents": 0, "cases": config.FREE_CASES,
                 "features": [tr('{FREE_CASES} situations of your own', FREE_CASES=config.FREE_CASES), tr('All storylines to practise with'), tr('Documents, journal and follow-ups')]},
        "pass": {"id": PLAN, "name": tr('First {PASS_DAYS} Days Pass', PASS_DAYS=config.PASS_DAYS), "priceCents": config.PASS_PRICE_CENTS, "days": config.PASS_DAYS,
                 "billing": tr('one-time payment, no subscription'),
                 "features": [tr('Unlimited situations'), tr('Every new situation we add during your pass'), tr('AI drafts when available'),
                              tr('Keep all documents after the pass ends')]},
        "testCheckout": config.TEST_CHECKOUT,
    }


def active_pass(db: Session, user_id: int) -> Purchase | None:
    return db.scalar(select(Purchase).where(Purchase.user_id == user_id, Purchase.expires_at > datetime.now(timezone.utc))
                     .order_by(Purchase.expires_at.desc()).limit(1))


def own_cases(db: Session, user_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Case).where(Case.user_id == user_id, Case.seeded.is_(False))) or 0


def status(db: Session, user_id: int) -> dict:
    p = active_pass(db, user_id)
    used = own_cases(db, user_id)
    return {"plan": "pass" if p else "free", "used": used, "limit": None if p else config.FREE_CASES,
            "remaining": None if p else max(0, config.FREE_CASES - used),
            "pass": {"expiresAt": p.expires_at.isoformat(), "provider": p.provider} if p else None}


def can_start_case(db: Session, user_id: int) -> bool:
    return bool(active_pass(db, user_id)) or own_cases(db, user_id) < config.FREE_CASES


def grant_pass(db: Session, user_id: int, provider: str) -> Purchase:
    """Extends an active pass instead of overlapping it."""
    current = active_pass(db, user_id)
    start = current.expires_at if current else datetime.now(timezone.utc)
    p = Purchase(user_id=user_id, plan=PLAN, amount_cents=config.PASS_PRICE_CENTS, provider=provider,
                 expires_at=start + timedelta(days=config.PASS_DAYS))
    db.add(p)
    return p
