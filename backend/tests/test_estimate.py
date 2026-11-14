"""Estimate and promise: PERT numbers by hand, risk, validation and the full API flow."""
from app import packs
from app.engine import estimate
from app.validate import validate_answers

INPUTS = {"title": "Churn report", "context": "", "optimisticHours": 8, "likelyHours": 16, "pessimisticHours": 40, "hoursPerWeek": 20,
          "interruptionsPct": 20, "startDate": "2026-11-16", "requester": "manager", "costOfLate": "medium",
          "askedDeadline": "2026-11-24", "asOf": "2026-11-16"}  # a Monday


def opt(r, key):
    return next(o for o in r["options"] if o["key"] == key)


def test_numbers_by_hand():
    r = estimate.compute(INPUTS)
    # mean = (8 + 64 + 40) / 6 = 18.67 h, sd = 32 / 6 = 5.33 h, 20 h a week * 80 % = 3.2 real hours a day
    assert r["meanHours"] == 18.7 and r["sdHours"] == 5.3 and r["hoursPerDay"] == 3.2
    assert (opt(r, "optimistic")["workdays"], opt(r, "likely")["workdays"], opt(r, "safe")["workdays"]) == (3, 5, 8)  # ceil(8/3.2), 16/3.2, 25.49/3.2
    assert [opt(r, k)["date"] for k in ("optimistic", "likely", "safe", "range")] == ["2026-11-19", "2026-11-23", "2026-11-26", "2026-11-26"]
    # chance = Phi((days * 3.2 - 18.67) / 5.33): Phi(-1.70) = 4 %, Phi(-0.50) = 31 %, Phi(1.30) = 90 %
    assert [opt(r, k)["probability"] for k in ("optimistic", "likely", "safe", "range")] == [4, 31, 90, 90]
    assert [opt(r, k)["lateDays"] for k in ("optimistic", "likely", "safe", "range")] == [0, 0, 2, 2]  # asked for Tuesday the 24th
    # risk: miss 4 + 1 (medium cost, chance < 65 %) = 5; miss 3 + 1 = 4; safe: 0 + 1 (2 days after the ask) = 1; range the same
    assert [opt(r, k)["riskScore"] for k in ("optimistic", "likely", "safe", "range")] == [5, 4, 1, 1]
    assert [opt(r, k)["riskLevel"] for k in ("optimistic", "likely", "safe", "range")] == ["high", "high", "low", "low"]
    assert r["lowestRiskKey"] == "safe"  # ties keep the list order
    rg = opt(r, "range")
    assert rg["dateFrom"] == "2026-11-23" and rg["recheckDate"] == "2026-11-19"  # half of 16 h = 2.5 days -> 3 working days
    assert estimate.compute(INPUTS) == r  # deterministic


def test_client_and_high_cost_weigh_more_and_no_deadline_means_no_lateness():
    r = estimate.compute({**INPUTS, "requester": "client", "costOfLate": "high", "askedDeadline": ""})
    assert opt(r, "optimistic")["riskScore"] == 4 + 2 + 1 and all(o["lateDays"] == 0 for o in r["options"])
    assert opt(r, "safe")["riskScore"] == 0 and r["lowestRiskKey"] == "safe"


def test_validation_and_cross_field_rule():
    qs = packs.get_situation("asked-for-a-deadline")["questions"]
    values, errors = validate_answers(qs, {k: v for k, v in INPUTS.items() if k != "asOf"})
    assert not errors and values["askedDeadline"] == "2026-11-24"
    assert set(estimate.check({**INPUTS, "likelyHours": 5})) == {"likelyHours"}
    assert set(estimate.check({**INPUTS, "pessimisticHours": 10})) == {"pessimisticHours"}
    assert estimate.check(INPUTS) == {}
    _, errors = validate_answers(qs, {**INPUTS, "interruptionsPct": 95, "requester": "ceo"})
    assert {"interruptionsPct", "requester"} <= set(errors)


def test_estimate_flow_through_api(client):
    client.post("/api/auth/register", json={"email": "est@example.com", "password": "correct-horse"})
    client.put("/api/profile", json={"roleId": "specialist-new-company", "industry": "", "tenure": "1-3m", "fears": []})
    body = {"situationId": "asked-for-a-deadline", "privacyAck": True, "confidenceBefore": 2, "inputs": {k: v for k, v in INPUTS.items() if k != "asOf"}}
    bad = client.post("/api/cases", json={**body, "inputs": {**body["inputs"], "likelyHours": 5}})
    assert bad.status_code == 400 and "likelyHours" in bad.json()["fields"]
    made = client.post("/api/cases", json=body).json()["case"]
    assert made["title"] == "Churn report" and [o["key"] for o in made["result"]["options"]] == ["optimistic", "likely", "safe", "range"]
    assert client.post(f"/api/cases/{made['id']}/decision", json={"option": "accept"}).status_code == 400
    case = client.post(f"/api/cases/{made['id']}/decision", json={"option": "range", "rationale": "Estimate spread is wide"}).json()["case"]
    assert case["document"].startswith("# Estimate reply: Churn report") and "between" in case["document"] and "re-check" in case["document"].lower()
    assert case["debrief"]["points"] and client.post(f"/api/cases/{made['id']}/hint", json={}).status_code in (404, 409)
    assert client.get("/api/documents").json()["documents"][0]["label"] == "Estimate reply"
    pub = {s["id"]: s for s in client.get("/api/packs").json()["situations"]}["asked-for-a-deadline"]
    assert len(pub["storylines"]) == 3 and len(pub["storylines"][0]["answers"]["askedDeadline"]) == 10  # relative dates resolved
    assert "*" in pub["applies_to"]
