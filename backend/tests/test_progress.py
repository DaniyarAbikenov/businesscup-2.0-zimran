"""Progress aggregation (hand-checked numbers) and the opt-in emails: who gets them, once, one-click links, unsubscribe."""
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app import emails
from app.cache import get_redis
from app.db import SessionLocal, engine
from test_api import signup

TASKS = [{"name": "Report", "effortHours": 14, "deadline": "2030-01-23", "requester": "manager", "impact": "reputation", "note": ""},
         {"name": "Data pull", "effortHours": 6, "deadline": "2030-01-18", "requester": "peer", "impact": "money", "note": ""}]
PRIO = {"title": "Two asks", "context": "SECRET-CONTEXT", "tasks": TASKS, "hoursPerWeek": 40, "committedHours": 15}


def setup_user(c, email="p@example.com", role="specialist-new-company"):
    signup(c, email)
    assert c.put("/api/profile", json={"roleId": role, "industry": "", "tenure": "1-3m", "fears": []}).status_code == 200
    return c


def start(c, title="Two asks", conf=2):
    r = c.post("/api/cases", json={"situationId": "competing-priorities", "privacyAck": True, "confidenceBefore": conf, "inputs": {**PRIO, "title": title}})
    assert r.status_code == 201
    return r.json()["case"]["id"]


def decide(c, cid):
    return c.post(f"/api/cases/{cid}/decision", json={"option": "deadline", "rationale": "x", "followupDays": 3}).json()["case"]


def make_due(cid):
    with engine.begin() as conn:
        conn.execute(text("UPDATE decisions SET followup_due = CURRENT_DATE - 1 WHERE case_id = :c"), {"c": cid})


def outbox():
    return [__import__("json").loads(x) for x in get_redis().lrange("outbox", 0, -1)]


def run(fn, **kw):
    with SessionLocal() as db:
        return fn(db, get_redis(), **kw)


def test_progress_empty_user(client):
    setup_user(client)
    p = client.get("/api/progress").json()
    assert p["day"] == 1 and p["inWindow"] and p["timeline"] == [] and p["confidence"] == [] and p["averageChange"] is None
    assert p["counts"] == {"situations": 0, "decisions": 0, "followups": 0, "documents": 0, "exported": 0}
    assert p["practiced"] == [] and p["outcomesTotal"] == 0 and p["inactiveHint"] is False
    assert p["tryNext"]["id"] == "competing-priorities" and p["emailReminders"] is False and p["logMailer"] is True


def test_progress_numbers_by_hand(client):
    setup_user(client)
    a = start(client, "First", conf=2)
    b = start(client, "Second", conf=3)
    c = start(client, "Third draft", conf=4)
    decide(client, a)
    decide(client, b)
    client.post(f"/api/cases/{a}/reflection", json={"learned": "x", "different": "y", "confidenceAfter": 4})  # +2
    client.post(f"/api/cases/{b}/reflection", json={"learned": "x", "different": "y", "confidenceAfter": 4})  # +1
    client.post(f"/api/cases/{a}/followup", json={"outcome": "worked", "notes": ""})
    client.post(f"/api/cases/{a}/export", json={"how": "copy"})
    make_due(b)
    p = client.get("/api/progress").json()
    assert p["counts"] == {"situations": 3, "decisions": 2, "followups": 1, "documents": 2, "exported": 1}
    assert p["averageChange"] == 1.5 and [x["before"] for x in p["confidence"]] == [2, 3] and [x["after"] for x in p["confidence"]] == [4, 4]
    assert [t["title"] for t in p["timeline"]] == ["Third draft", "Second", "First"]  # newest first
    assert [t["status"] for t in p["timeline"]] == ["draft", "due", "done"]
    assert p["timeline"][2]["outcomeLabel"] == "It worked" and p["timeline"][2]["chosen"] == "Earliest deadline first"
    assert p["outcomes"]["worked"] == 1 and p["outcomesTotal"] == 1
    assert p["practiced"] == [{"category": "Workload and priorities", "situations": [{"title": "Several urgent asks, not enough time", "count": 3}]}]
    assert p["firsts"]["situation"] and p["firsts"]["decision"] and p["firsts"]["debrief"]
    assert p["tryNext"]["id"] == "asked-for-a-deadline"  # the next catalog entry for this role that was not tried yet


def test_progress_is_per_user(client, make_client):
    setup_user(client)
    start(client)
    other = setup_user(make_client(), "other@example.com")
    assert other.get("/api/progress").json()["counts"]["situations"] == 0
    assert make_client().get("/api/progress").status_code == 401


def test_emails_only_for_opted_in_due_once(client):
    setup_user(client)
    cid = start(client, "Launch plan")
    decide(client, cid)
    make_due(cid)
    assert run(emails.send_due_followups) == 0  # not opted in
    assert client.post("/api/progress/reminders", json={"enabled": "yes"}).status_code == 400
    assert client.post("/api/progress/reminders", json={"enabled": True}).json() == {"emailReminders": True}
    assert client.get("/api/me").json()["profile"]["emailReminders"] is True
    later = start(client, "Not due yet")
    decide(client, later)
    assert run(emails.send_due_followups) == 1 and run(emails.send_due_followups) == 0  # once only
    mails = outbox()
    assert len(mails) == 1 and mails[0]["to"] == "p@example.com" and "Launch plan" in mails[0]["subject"]
    assert f"/case/{cid}" in mails[0]["body"] and "/api/unsubscribe/" in mails[0]["body"]
    assert "SECRET-CONTEXT" not in mails[0]["body"] and "Report" not in mails[0]["body"]  # only the title, no inputs
    assert "Not due yet" not in mails[0]["body"]


def test_no_email_for_demo_users_or_answered_followups(client, make_client):
    demo = setup_user(client, "demo-1@demo.roleshift.local")
    cid = start(demo)
    decide(demo, cid)
    make_due(cid)
    demo.post("/api/progress/reminders", json={"enabled": True})
    assert run(emails.send_due_followups) == 0 and outbox() == []
    real = setup_user(make_client(), "real@example.com")
    c2 = start(real)
    decide(real, c2)
    real.post("/api/progress/reminders", json={"enabled": True})
    real.post(f"/api/cases/{c2}/followup", json={"outcome": "partly", "notes": ""})
    make_due(c2)
    assert run(emails.send_due_followups) == 0  # already answered


def test_one_click_outcome_single_use_and_expiry(client, make_client):
    setup_user(client)
    cid = start(client, "Roll-out")
    decide(client, cid)
    client.post("/api/progress/reminders", json={"enabled": True})
    make_due(cid)
    assert run(emails.send_due_followups) == 1
    toks = re.findall(r"/api/followup/(\S+)", outbox()[0]["body"])
    assert len(toks) == 3
    anon = make_client()  # no session: the links work without signing in
    assert anon.get("/api/followup/not-a-token").status_code == 404
    page = anon.get(f"/api/followup/{toks[1]}")
    assert page.status_code == 200 and f"/case/{cid}" in page.text and "refresh" in page.text
    case = client.get(f"/api/cases/{cid}").json()["case"]
    assert case["followup"]["outcome"] == "partly"
    assert anon.get(f"/api/followup/{toks[1]}").status_code == 404  # single use
    assert anon.get(f"/api/followup/{toks[0]}").status_code == 404  # the other outcome links of the case stop working too
    assert client.get(f"/api/cases/{cid}").json()["case"]["followup"]["outcome"] == "partly"
    # expired
    cid2 = start(client, "Second roll-out")
    decide(client, cid2)
    make_due(cid2)
    run(emails.send_due_followups)
    t2 = re.findall(r"/api/followup/(\S+)", outbox()[0]["body"])[0]
    with engine.begin() as conn:
        conn.execute(text("UPDATE email_tokens SET expires_at = now() - interval '1 day'"))
    assert anon.get(f"/api/followup/{t2}").status_code == 404
    assert client.get(f"/api/cases/{cid2}").json()["case"]["followup"] is None


def test_unsubscribe_without_signing_in(client, make_client):
    setup_user(client)
    cid = start(client)
    decide(client, cid)
    client.post("/api/progress/reminders", json={"enabled": True})
    make_due(cid)
    run(emails.send_due_followups)
    tok = re.search(r"/api/unsubscribe/(\S+)", outbox()[0]["body"]).group(1)
    anon = make_client()
    assert anon.get("/api/unsubscribe/wrong").status_code == 404
    assert anon.get(f"/api/unsubscribe/{tok}").status_code == 200
    assert client.get("/api/me").json()["profile"]["emailReminders"] is False
    later = start(client, "Later")
    decide(client, later)
    make_due(later)
    assert run(emails.send_due_followups) == 0  # off again


def test_day7_nudge_once_and_only_when_needed(client, make_client):
    setup_user(client)
    client.post("/api/progress/reminders", json={"enabled": True})
    assert run(emails.send_day7_nudges) == 0  # signed up today
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET created_at = now() - interval '8 days'"))
    assert run(emails.send_day7_nudges) == 1 and run(emails.send_day7_nudges) == 0
    assert outbox()[0]["subject"] == "Pick your next scenario" and "/api/unsubscribe/" in outbox()[0]["body"]
    busy = setup_user(make_client(), "busy@example.com")
    busy.post("/api/progress/reminders", json={"enabled": True})
    start(busy), start(busy)
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET created_at = now() - interval '8 days'"))
    assert run(emails.send_day7_nudges) == 0  # two situations already: no nudge


def test_send_now_endpoint(client):
    setup_user(client)
    assert client.post("/api/progress/send-reminders-now", json={}).status_code == 409  # not opted in
    client.post("/api/progress/reminders", json={"enabled": True})
    cid = start(client)
    decide(client, cid)
    make_due(cid)
    assert client.post("/api/progress/send-reminders-now", json={}).json() == {"sent": 1, "logMailer": True}
