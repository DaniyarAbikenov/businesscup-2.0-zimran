"""Decision calculator: scores, ranks, strategies and flip points by hand, validation, API flow."""
from app import packs
from app.engine import decision
from app.validate import validate_answers

CRIT = [{"name": "Price", "weight": 5}, {"name": "Fit", "weight": 3}, {"name": "Risk", "weight": 2}]
OPTS = [{"name": "A", "note": "", "s1": 4, "s2": 3, "s3": 2}, {"name": "B", "note": "", "s1": 3, "s2": 5, "s3": 4}, {"name": "C", "note": "", "s1": 5, "s2": 2, "s3": 3}]
INPUTS = {"title": "Pick a tool", "context": "", "criteria": CRIT, "options": OPTS, "reversibility": "cannot", "whoAffected": "client",
          "confidence": "low", "decideBy": "", "asOf": "2026-11-16"}


def opt(r, key):
    return next(o for o in r["options"] if o["key"] == key)


def test_scores_ranks_and_strategies_by_hand():
    r = decision.compute(INPUTS)
    # A = 5*4 + 3*3 + 2*2 = 33 of 50 -> 66.0, B = 15 + 15 + 8 = 38 -> 76.0, C = 25 + 6 + 6 = 37 -> 74.0
    assert [(x["name"], x["score"], x["rank"]) for x in r["ranking"]] == [("B", 76.0, 1), ("C", 74.0, 2), ("A", 66.0, 3)]
    assert [x["marginToNext"] for x in r["ranking"]] == [2.0, 8.0, None]
    assert r["robustness"] == {"label": "too close to call", "margin": 2.0}  # 2 points < 4
    # best: B. safest: worst scores A 2, B 3, C 2 -> B. equal weights: 9, 12, 10 -> B. heaviest (Price, Fit): 29, 30, 31 -> C
    assert [opt(r, k)["pick"] for k in ("best", "safest", "equal", "heaviest")] == ["B", "B", "B", "C"]
    assert opt(r, "best")["sameAs"] == ["safest", "equal"] and opt(r, "heaviest")["sameAs"] == [] and r["agree"] is False
    # B lowered by 1 on Risk (weight 2, the cheapest flip): 38 - 2 = 36 < 37
    assert r["flipScore"] == {"side": "winner", "criterion": "Risk", "from": 4, "to": 3, "points": 1, "option": "B"}
    # Fit 3 -> 2: A 30, B 33, C 35 -> C wins. (Price 5 -> 4 still B)
    assert r["flipWeight"] == {"criterion": "Fit", "from": 3, "to": 2, "newWinner": "C"}
    # shared risk: impact = cannot (2) + client (1) = 3, uncertainty = too close (2) + low confidence (2) = 4 -> min(3, 12 // 2) = 3
    assert [opt(r, k)["riskScore"] for k in ("best", "safest", "equal", "heaviest")] == [3, 3, 3, 3 + 1 + 1]  # heaviest: 2 points lower, Fit 2
    assert opt(r, "heaviest")["riskLevel"] == "high" and r["lowestRiskKey"] == "best"
    assert decision.compute(INPUTS) == r


def test_easy_decision_and_robust_winner():
    easy = {**INPUTS, "reversibility": "easy", "whoAffected": "me", "confidence": "high"}
    r = decision.compute(easy)
    assert [opt(r, k)["riskScore"] for k in ("best", "safest", "equal")] == [0, 0, 0] and "No warning signs" in opt(r, "best")["risks"][0]["text"]
    far = {**easy, "options": [{**OPTS[1]}, {"name": "Weak", "note": "", "s1": 1, "s2": 1, "s3": 1}]}
    r = decision.compute(far)
    assert r["robustness"]["label"] == "robust" and r["flipScore"] is None and r["flipWeight"] is None
    assert "No single score change" in r["notes"][1] and "does not change" in r["notes"][2]


def test_validation_and_scores_check():
    qs = packs.get_situation("choose-between-options")["questions"]
    body = {k: v for k, v in INPUTS.items() if k != "asOf"}
    values, errors = validate_answers(qs, body)
    assert not errors and values["options"][1]["s2"] == 5 and values["criteria"][0]["weight"] == 5
    assert decision.check(values) == {}
    missing = {**body, "options": [OPTS[0], {"name": "B", "note": "", "s1": 3, "s2": 9, "s3": ""}]}
    _, errors = validate_answers(qs, missing)
    assert "options.1.s2" in errors  # out of range
    values, errors = validate_answers(qs, {**body, "options": [OPTS[0], {"name": "B", "note": "", "s1": 3, "s2": 4}]})
    assert not errors and set(decision.check(values)) == {"options.1.s3"}  # a score for every criterion is required
    _, errors = validate_answers(qs, {**body, "options": [OPTS[0]]})
    assert "options" in errors  # at least two options
    _, errors = validate_answers(qs, {**body, "criteria": [{"name": "Price", "weight": 7}, CRIT[1]]})
    assert "criteria.0.weight" in errors


def test_decision_flow_through_api(client):
    client.post("/api/auth/register", json={"email": "dec@example.com", "password": "correct-horse"})
    client.put("/api/profile", json={"roleId": "career-switch", "industry": "", "tenure": "1-3m", "fears": []})
    body = {"situationId": "choose-between-options", "privacyAck": True, "confidenceBefore": 2, "inputs": {k: v for k, v in INPUTS.items() if k != "asOf"}}
    bad = client.post("/api/cases", json={**body, "inputs": {**body["inputs"], "options": [OPTS[0], {"name": "B", "s1": 3, "s2": 4}]}})
    assert bad.status_code == 400 and "options.1.s3" in bad.json()["fields"]
    made = client.post("/api/cases", json=body).json()["case"]
    assert made["title"] == "Pick a tool" and [o["key"] for o in made["result"]["options"]] == ["best", "safest", "equal", "heaviest"]
    assert client.post(f"/api/cases/{made['id']}/decision", json={"option": "accept"}).status_code == 400
    case = client.post(f"/api/cases/{made['id']}/decision", json={"option": "heaviest", "rationale": "Price and fit matter most"}).json()["case"]
    doc = case["document"]
    assert doc.startswith("# Decision note: Pick a tool") and "too close to call" in doc and "What would change the result" in doc
    assert "| B | 76" in doc and "Price (5)" in doc and "Price and fit matter most" in doc
    assert case["debrief"]["points"][0].startswith("On your numbers") and client.post(f"/api/cases/{made['id']}/hint", json={}).status_code in (404, 409)
    assert client.get("/api/documents").json()["documents"][0]["label"] == "Decision note"
    pub = {s["id"]: s for s in client.get("/api/packs").json()["situations"]}["choose-between-options"]
    assert "*" in pub["applies_to"] and len(pub["storylines"]) >= 3
    for st in pub["storylines"]:  # every storyline passes the same validation as the form
        values, errors = validate_answers(pub["questions"], st["answers"])
        assert not errors and not decision.check(values), (st["id"], errors)
