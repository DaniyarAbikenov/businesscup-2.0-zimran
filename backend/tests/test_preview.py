"""Live preview: stateless, needs a sign-in, says what is missing, and matches the saved calculation."""
from app import packs

PRIO = {"title": "Asks", "context": "", "hoursPerWeek": 40, "committedHours": 15,
        "tasks": [{"name": "Report", "effortHours": 14, "deadline": "2030-01-23", "requester": "manager", "impact": "reputation", "note": ""},
                  {"name": "Data", "effortHours": 6, "deadline": "2030-01-18", "requester": "peer", "impact": "money", "note": ""}]}


def signup(client):
    client.post("/api/auth/register", json={"email": "pv@example.com", "password": "correct-horse"})
    client.put("/api/profile", json={"roleId": "it-pm", "industry": "", "tenure": "1-3m", "fears": []})


def test_preview_needs_sign_in(client):
    assert client.post("/api/cases/preview", json={"situationId": "competing-priorities", "inputs": PRIO}).status_code == 401


def test_not_ready_lists_what_is_missing_and_saves_nothing(client):
    signup(client)
    r = client.post("/api/cases/preview", json={"situationId": "competing-priorities", "inputs": {"hoursPerWeek": 40}}).json()
    assert r["ready"] is False and "What is going on, in one line?" in r["needed"] and len(r["needed"]) <= 6
    assert client.get("/api/journal").json()["cases"] == []


def test_ready_matches_the_saved_case_and_has_safe_facts(client):
    signup(client)
    r = client.post("/api/cases/preview", json={"situationId": "competing-priorities", "inputs": PRIO}).json()
    assert r["ready"] and r["hasGuess"] is True
    assert r["facts"] == [{"key": "totalHours", "value": 20, "unit": "h"}, {"key": "freeHoursPerDay", "value": 5, "unit": "h"}]  # 14 + 6 hours; 25 free hours a week = 5 a day
    saved = client.post("/api/cases", json={"situationId": "competing-priorities", "privacyAck": True, "confidenceBefore": 3, "inputs": PRIO}).json()["case"]
    assert saved["result"]["lowestRiskKey"] == r["result"]["lowestRiskKey"] and saved["result"]["totalHours"] == r["result"]["totalHours"]
    assert len(client.get("/api/journal").json()["cases"]) == 1  # only the one saved on purpose


def test_change_request_has_no_guess_step(client):
    signup(client)
    sit = packs.get_situation("client-change-request")
    pub = packs.public_pack_situation("client-change-request")
    defaults = {q["id"]: q["default"] for q in pub["questions"] if "default" in q}
    r = client.post("/api/cases/preview", json={"situationId": sit["id"], "inputs": {**defaults, **pub["storylines"][0]["answers"]}}).json()
    assert r["ready"] and r["hasGuess"] is False and r["facts"][0]["key"] == "workdaysToRelease"
