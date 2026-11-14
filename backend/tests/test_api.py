from app.cache import get_redis

ANSWERS = dict(
    changeTitle="Add CSV export", requestedBy="Jordan", priority="important", releaseDate="2026-12-15",
    teamSize=6, dailyRate=600, budgetRemaining=40000, changeEffortDays=10, bufferDays=2,
    clientCoversPct=0, overheadPct=25, parallelPct=60, focusPct=70,
)


def signup(c, email, pw="correct-horse"):
    r = c.post("/api/auth/register", json={"email": email, "password": pw})
    assert r.status_code == 201
    return c


def test_auth_rules(client, make_client):
    assert client.post("/api/auth/register", json={"email": "bad", "password": "longenough"}).status_code == 400
    assert client.post("/api/auth/register", json={"email": "a@b.co", "password": "short"}).status_code == 400
    signup(client, "ann@example.com")
    assert make_client().post("/api/auth/register", json={"email": "ANN@example.com", "password": "correct-horse"}).status_code == 409
    assert make_client().get("/api/me").status_code == 401
    assert client.get("/api/me").json()["user"]["email"] == "ann@example.com"

    other = make_client()
    assert other.post("/api/auth/login", json={"email": "ann@example.com", "password": "nope-nope"}).status_code == 401
    assert other.post("/api/auth/login", json={"email": "ann@example.com", "password": "correct-horse"}).status_code == 200
    assert other.get("/api/me").status_code == 200
    other.post("/api/auth/logout", json={})
    assert other.get("/api/me").status_code == 401  # session removed from Redis


def test_login_throttle(client):
    signup(client, "t@example.com")
    c = client.__class__(client.app)
    for _ in range(10):
        assert c.post("/api/auth/login", json={"email": "t@example.com", "password": "wrong-pass"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": "t@example.com", "password": "correct-horse"}).status_code == 429


def test_non_json_write_rejected(client):
    r = client.post("/api/auth/login", content="x", headers={"content-type": "text/plain"})
    assert r.status_code == 415


def test_full_flow(client):
    signup(client, "flow@example.com")
    assert client.put("/api/profile", json={"roleId": "nope", "tenure": "1-3m"}).status_code == 400
    p = client.put("/api/profile", json={"roleId": "it-pm", "industry": "Fintech", "tenure": "1-3m", "fears": ["wrong-call", "bogus"]})
    assert p.json()["profile"]["fears"] == ["wrong-call"]

    bad = client.post("/api/cases", json={"situationId": "client-change-request", "privacyAck": True, "confidenceBefore": 2, "inputs": {**ANSWERS, "teamSize": -1}})
    assert bad.status_code == 400 and "teamSize" in bad.json()["fields"]

    no_ack = client.post("/api/cases", json={"situationId": "client-change-request", "confidenceBefore": 2, "inputs": ANSWERS})
    assert no_ack.status_code == 400 and "confidential" in no_ack.json()["error"]
    made = client.post("/api/cases", json={"situationId": "client-change-request", "privacyAck": True, "confidenceBefore": 2, "inputs": ANSWERS})
    assert made.status_code == 201
    cid = made.json()["case"]["id"]
    assert len(made.json()["case"]["result"]["options"]) == 3

    d = client.post(f"/api/cases/{cid}/decision", json={"option": "accept", "rationale": "Funded by phase 2", "followupDays": 2})
    assert d.status_code == 200
    case = d.json()["case"]
    assert "# Change Request: Add CSV export" in case["document"] and case["debrief"]["points"]
    assert client.post(f"/api/cases/{cid}/decision", json={"option": "defer"}).status_code == 409

    # Redis reminder index: due in 2 days, so nothing is due yet but the entry exists
    assert get_redis().zcard("followups:1") == 1
    assert client.get("/api/reminders").json()["due"] == 0

    assert client.post(f"/api/cases/{cid}/reflection", json={"confidenceAfter": 9}).status_code == 400
    client.post(f"/api/cases/{cid}/reflection", json={"learned": "Ask for estimates", "confidenceAfter": 4})
    fu = client.post(f"/api/cases/{cid}/followup", json={"outcome": "worked", "notes": "Client signed"})
    assert fu.json()["case"]["followup"]["outcome"] == "worked"
    assert get_redis().zcard("followups:1") == 0

    j = client.get("/api/journal").json()
    assert j["stats"] == {"started": 1, "decided": 1, "exported": 0, "followedUp": 1, "reportedWorked": 1, "confidenceChange": 2.0}
    assert j["followups"] == [] and any(e["type"] == "followup" for e in j["entries"])


def test_ownership(client, make_client):
    signup(client, "owner@example.com")
    intruder = signup(make_client(), "intruder@example.com")
    cid = client.post("/api/cases", json={"situationId": "client-change-request", "privacyAck": True, "confidenceBefore": 3, "inputs": ANSWERS}).json()["case"]["id"]
    assert intruder.get(f"/api/cases/{cid}").status_code == 404
    assert intruder.post(f"/api/cases/{cid}/decision", json={"option": "accept"}).status_code == 404
    assert intruder.put(f"/api/cases/{cid}/inputs", json={"inputs": ANSWERS}).status_code == 404
    assert client.get(f"/api/cases/{cid}").status_code == 200
    assert intruder.get("/api/journal").json()["stats"]["started"] == 0


def test_recalculate_draft_only(client):
    signup(client, "re@example.com")
    cid = client.post("/api/cases", json={"situationId": "client-change-request", "privacyAck": True, "confidenceBefore": 3, "inputs": ANSWERS}).json()["case"]["id"]
    r = client.put(f"/api/cases/{cid}/inputs", json={"inputs": {**ANSWERS, "changeEffortDays": 1, "bufferDays": 9}})
    assert r.json()["case"]["result"]["options"][0]["slipWorkdays"] == 0
    client.post(f"/api/cases/{cid}/decision", json={"option": "decline"})
    assert client.put(f"/api/cases/{cid}/inputs", json={"inputs": ANSWERS}).status_code == 409


def test_demo_account_has_every_step(client, monkeypatch):
    assert client.get("/api/public-config").json() == {"demoEnabled": True}
    assert client.post("/api/auth/demo", json={}).status_code == 201
    assert client.get("/api/me").json()["isDemo"] is True
    j = client.get("/api/journal").json()
    assert j["stats"]["started"] == 4 and j["stats"]["decided"] == 2 and j["stats"]["followedUp"] == 1
    assert j["stats"]["confidenceChange"] == 2.0
    assert len(j["followups"]) == 1 and j["followups"][0]["overdue"] is True
    assert client.get("/api/reminders").json()["due"] == 1
    drafts = {c["title"]: c["id"] for c in j["cases"] if c["status"] == "draft"}
    assert set(drafts) == {"Add dark mode to the dashboard", "Three urgent asks in my first month"}
    cr = drafts["Add dark mode to the dashboard"]
    assert client.post(f"/api/cases/{cr}/decision", json={"option": "defer"}).status_code == 200
    prio = client.get(f"/api/cases/{drafts['Three urgent asks in my first month']}").json()["case"]
    assert prio["situationId"] == "competing-priorities" and len(prio["result"]["options"]) == 4


def test_demo_can_be_switched_off(client, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "DEMO_MODE", False)
    assert client.post("/api/auth/demo", json={}).status_code == 404


def test_client_log_accepts_events_without_login(client):
    r = client.post("/api/client-log", json={"events": [{"level": "error", "event": "window.error", "message": "boom", "meta": {"line": 3}}]})
    assert r.status_code == 202 and r.json() == {"accepted": 1}
    assert r.headers["x-request-id"]
    assert client.post("/api/client-log", json={"events": [{"event": "x"}] * 21}).status_code == 400  # batch too large
    assert client.post("/api/client-log", data="x", headers={"content-type": "text/plain"}).status_code == 415


def test_documents_are_saved_and_versioned(client, make_client):
    signup(client, "docs@example.com")
    cid = client.post("/api/cases", json={"situationId": "client-change-request", "privacyAck": True, "confidenceBefore": 3, "inputs": ANSWERS}).json()["case"]["id"]
    assert client.put(f"/api/cases/{cid}/documents/change_request", json={"body": "x"}).status_code == 409  # not decided yet
    case = client.post(f"/api/cases/{cid}/decision", json={"option": "accept"}).json()["case"]
    generated = case["document"]
    assert case["documentRevisions"] == 1

    edited = generated + "\n\nMy note"
    saved = client.put(f"/api/cases/{cid}/documents/change_request", json={"body": edited}).json()["case"]
    assert saved["document"] == edited and saved["documentRevisions"] == 2
    # saving identical text adds nothing; the edit survives a fresh load
    assert client.put(f"/api/cases/{cid}/documents/change_request", json={"body": edited}).json()["case"]["documentRevisions"] == 2
    assert client.get(f"/api/cases/{cid}").json()["case"]["document"] == edited
    revs = client.get(f"/api/cases/{cid}/documents/change_request/revisions").json()["revisions"]
    assert [r["source"] for r in revs] == ["user", "generated"] and revs[1]["body"] == generated

    assert client.put(f"/api/cases/{cid}/documents/client_message", json={"body": "Hi [Name]"}).json()["case"]["clientMessage"] == "Hi [Name]"
    assert client.put(f"/api/cases/{cid}/documents/change_request", json={"body": "  "}).status_code == 400
    assert client.put(f"/api/cases/{cid}/documents/nope", json={"body": "x"}).status_code == 404

    lib = client.get("/api/documents").json()["documents"]
    assert {d["kind"] for d in lib} == {"change_request", "client_message"}
    assert any(e["type"] == "document" for e in client.get("/api/journal").json()["entries"])

    other = signup(make_client(), "docs2@example.com")
    assert other.put(f"/api/cases/{cid}/documents/change_request", json={"body": "hijack"}).status_code == 404
    assert other.get(f"/api/cases/{cid}/documents/change_request/revisions").status_code == 404
    assert other.get("/api/documents").json()["documents"] == []


def test_export_is_recorded_and_account_can_be_deleted(client, make_client):
    signup(client, "gone@example.com")
    client.put("/api/profile", json={"roleId": "it-pm", "industry": "", "tenure": "1-3m", "fears": []})
    cid = client.post("/api/cases", json={"situationId": "client-change-request", "privacyAck": True, "confidenceBefore": 3, "inputs": ANSWERS}).json()["case"]["id"]
    assert client.post(f"/api/cases/{cid}/export", json={"how": "copy"}).status_code == 409  # nothing to export yet
    client.post(f"/api/cases/{cid}/decision", json={"option": "accept", "followupDays": 2})
    assert client.post(f"/api/cases/{cid}/export", json={"how": "fax"}).status_code == 400
    assert client.post(f"/api/cases/{cid}/export", json={"how": "copy"}).status_code == 200
    assert client.post(f"/api/cases/{cid}/export", json={"how": "download"}).status_code == 200
    j = client.get("/api/journal").json()
    assert j["stats"]["exported"] == 1 and sum(e["type"] == "export" for e in j["entries"]) == 2

    other = signup(make_client(), "stays@example.com")
    other_case = other.post("/api/cases", json={"situationId": "client-change-request", "privacyAck": True, "confidenceBefore": 3, "inputs": ANSWERS}).json()["case"]["id"]

    assert client.request("DELETE", "/api/account", json={"confirm": "yes"}).status_code == 400
    assert client.request("DELETE", "/api/account", json={"confirm": "DELETE"}).status_code == 200
    assert client.get("/api/me").status_code == 401
    assert get_redis().zcard("followups:1") == 0
    # login no longer works, and the other user's data is untouched
    assert client.post("/api/auth/login", json={"email": "gone@example.com", "password": "correct-horse"}).status_code == 401
    assert other.get(f"/api/cases/{other_case}").status_code == 200
