"""Free limit, the public pricing endpoint and the built-in test checkout."""
from app import config

from test_api import ANSWERS, signup


def new_case(c):
    return c.post("/api/cases", json={"situationId": "client-change-request", "privacyAck": True, "confidenceBefore": 3, "inputs": ANSWERS})


def test_pricing_is_public(client):
    p = client.get("/api/pricing").json()
    assert p["pass"]["priceCents"] == config.PASS_PRICE_CENTS and p["free"]["cases"] == config.FREE_CASES and p["testCheckout"] is True


def test_free_limit_then_test_checkout(client):
    signup(client, "pay@example.com")
    for _ in range(config.FREE_CASES):
        assert new_case(client).status_code == 201
    assert client.get("/api/billing").json() == {"plan": "free", "used": 3, "limit": 3, "remaining": 0, "pass": None}
    blocked = new_case(client)
    assert blocked.status_code == 402 and "free situations" in blocked.json()["error"]
    # existing cases still work on the free plan
    cid = client.get("/api/journal").json()["cases"][0]["id"]
    assert client.post(f"/api/cases/{cid}/decision", json={"option": "accept"}).status_code == 200

    assert client.post("/api/billing/test-checkout", json={"plan": "pass90"}).status_code == 400  # not confirmed
    assert client.post("/api/billing/test-checkout", json={"plan": "gold", "confirm": True}).status_code == 400
    st = client.post("/api/billing/test-checkout", json={"plan": "pass90", "confirm": True}).json()
    assert st["plan"] == "pass" and st["limit"] is None and st["pass"]["provider"] == "test"
    first_expiry = st["pass"]["expiresAt"]
    assert new_case(client).status_code == 201
    # buying again extends the pass instead of overlapping it
    again = client.post("/api/billing/test-checkout", json={"plan": "pass90", "confirm": True}).json()
    assert again["pass"]["expiresAt"] > first_expiry
    assert any(e["type"] == "purchase" for e in client.get("/api/journal").json()["entries"])


def test_demo_sample_cases_do_not_use_the_free_limit(client):
    client.post("/api/auth/demo", json={})
    assert client.get("/api/billing").json()["remaining"] == config.FREE_CASES
    assert new_case(client).status_code == 201


def test_test_checkout_can_be_switched_off(client, monkeypatch):
    signup(client, "nopay@example.com")
    monkeypatch.setattr(config, "TEST_CHECKOUT", False)
    assert client.post("/api/billing/test-checkout", json={"plan": "pass90", "confirm": True}).status_code == 404
    assert client.get("/api/billing").status_code == 200
