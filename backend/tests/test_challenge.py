"""Challenge my numbers, "did I forget anything" and risk labels on the user's own numbers."""
from app import challenge, engine, packs
from test_api import signup

INPUTS = {"title": "Three asks", "context": "", "hoursPerWeek": 40, "committedHours": 15, "hiddenHours": 0, "forgotten": "", "asOf": "2026-11-16",
          "tasks": [{"name": "Report", "effortHours": 14, "deadline": "2026-11-23", "requester": "manager", "impact": "reputation", "note": ""},
                    {"name": "Data pull", "effortHours": 6, "deadline": "2026-11-18", "requester": "peer", "impact": "money", "note": ""},
                    {"name": "VP overview", "effortHours": 8, "deadline": "2026-11-19", "requester": "skip", "impact": "reputation", "note": ""}]}


def test_hidden_hours_reduce_free_time_and_appear_in_assumptions():
    sit = packs.get_situation("competing-priorities")
    base = engine.run(sit, INPUTS)
    more = engine.run(sit, {**INPUTS, "hiddenHours": 5})
    assert base["freeHoursPerDay"] == 5 and more["freeHoursPerDay"] == 4  # (40 - 15 - 5) / 5
    assert engine.check(sit, {**INPUTS, "hiddenHours": 25}) == {"committedHours": "Must be less than your working hours, or there is no time for these tasks"}
    est = packs.get_situation("asked-for-a-deadline")
    e = {"title": "x", "optimisticHours": 8, "likelyHours": 16, "pessimisticHours": 40, "hoursPerWeek": 20, "interruptionsPct": 20, "startDate": "2026-11-16",
         "requester": "manager", "costOfLate": "medium", "askedDeadline": "", "asOf": "2026-11-16"}
    assert engine.run(est, e)["hoursPerDay"] == 3.2 and engine.run(est, {**e, "hiddenHours": 4})["hoursPerDay"] == 2.6  # (20 - 4) / 5 * 0.8
    assert set(engine.check(est, {**e, "hiddenHours": 20})) == {"hiddenHours"}


def test_challenge_priorities_by_hand():
    sit = packs.get_situation("competing-priorities")
    result = engine.run(sit, INPUTS)
    labels = {k: v["label"] for k, v in sit["options"].items()}
    tests = challenge.run(sit, INPUTS, result, labels)
    assert len(tests) == 2 and tests[0]["what"] == "every estimate is 20% higher" and "unplanned" in tests[1]["what"]
    # the unplanned 4-hour task adds a fourth task with the earliest deadline: something more finishes late
    assert tests[1]["riskAfter"] in ("medium", "high") and isinstance(tests[1]["holds"], bool) and tests[1]["text"].startswith("If one unplanned")
    # a plan with no room at all "breaks" instead of crashing
    tight = {**INPUTS, "committedHours": 38, "hiddenHours": 0}
    broken = challenge.run(sit, tight, engine.run(sit, tight), labels)
    assert all("text" in t for t in broken)


def test_challenge_endpoint_and_dictionary(client):
    signup(client, "ch@example.com")
    client.put("/api/profile", json={"roleId": "promoted-to-lead", "industry": "", "tenure": "1-3m", "fears": []})
    body = {"situationId": "competing-priorities", "privacyAck": True, "confidenceBefore": 3, "inputs": {k: v for k, v in INPUTS.items() if k != "asOf"}}
    cid = client.post("/api/cases", json=body).json()["case"]["id"]
    r = client.get(f"/api/cases/{cid}/challenge").json()
    assert len(r["tests"]) == 2 and "allHold" in r
    ru = client.get(f"/api/cases/{cid}/challenge", headers={"x-lang": "ru"}).json()
    assert ru["tests"][0]["what"] == "каждая оценка на 20% выше" and ru["tests"][0]["text"].startswith("Если ")
    assert client.get(f"/api/cases/{cid + 99}/challenge").status_code == 404
    # decision, estimate and change request all answer too
    for sid in ("choose-between-options", "asked-for-a-deadline", "client-change-request"):
        pub = {s["id"]: s for s in client.get("/api/packs").json()["situations"]}[sid]
        defaults = {q["id"]: q["default"] for q in pub["questions"] if "default" in q}
        ans = {**defaults, **pub["storylines"][0]["answers"]}
        role = "it-pm" if sid == "client-change-request" else "promoted-to-lead"
        client.put("/api/profile", json={"roleId": role, "industry": "", "tenure": "1-3m", "fears": []})
        made = client.post("/api/cases", json={"situationId": sid, "privacyAck": True, "confidenceBefore": 3, "inputs": ans})
        if made.status_code == 402:
            break
        assert made.status_code == 201, sid
        assert len(client.get(f"/api/cases/{made.json()['case']['id']}/challenge").json()["tests"]) == 2
