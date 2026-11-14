from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import billing, config
from ..db import get_db
from ..deps import current_user
from ..errors import ApiError
from ..models import JournalEntry

router = APIRouter(prefix="/api")


@router.get("/pricing")
def pricing():
    """Public: the pricing page works without signing in."""
    return billing.plans()


@router.get("/billing")
def my_billing(user=Depends(current_user), db: Session = Depends(get_db)):
    return billing.status(db, user.id)


@router.post("/billing/test-checkout")
def test_checkout(body: dict, user=Depends(current_user), db: Session = Depends(get_db)):
    """Completes a purchase without a payment provider. Only when TEST_CHECKOUT is on; no card data is taken."""
    if not config.TEST_CHECKOUT:
        raise ApiError(404, "Test checkout is turned off")
    if body.get("plan") != billing.PLAN:
        raise ApiError(400, "Unknown plan")
    if body.get("confirm") is not True:
        raise ApiError(400, "Confirm the test purchase")
    p = billing.grant_pass(db, user.id, "test")
    db.add(JournalEntry(user_id=user.id, type="purchase",
                        text=f"Test purchase: {billing.plans()['pass']['name']} until {p.expires_at.date().isoformat()}. No money was charged."))
    db.commit()
    return billing.status(db, user.id)
