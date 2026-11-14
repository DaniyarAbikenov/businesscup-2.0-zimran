"""Competing priorities: orders, schedule, lateness, validation and the full API flow."""
from app import packs
from app.engine import priorities
from app.validate import validate_answers

TASKS = [
    {"name": "Report", "effortHours": 14, "deadline": "2026-11-23", "requester": "manager", "impact": "reputation", "note": ""},
    {"name": "Data pull", "effortHours": 6, "deadline": "2026-11-18", "requester": "peer", "impact": "money", "note": ""},
    {"name": "VP overview", "effortHours": 8, "deadline": "2026-11-19", "requester": "skip", "impact": "reputation", "note": ""},
]
INPUTS = {"title": "Three asks", "context": "", "tasks": TASKS, "hoursPerWeek": 40, "committedHours": 15, "asOf": "2026-11-16"}  # a Monday


def opt(r, key):
    return next(o for o in r["options"] if o["key"] == key)


def test_orders_and_schedule_by_hand():
    r = priorities.compute(INPUTS)  # 25 free hours a week = 5 a day
    assert r["freeHoursPerDay"] == 5 and r["totalHours"] == 28 and r["fits"] is False  # 25 h before the last deadline
    custom = opt(r, "custom")
    assert [s["finish"] for s in custom["schedule"]] == ["2026-11-19", "2026-11-20", "2026-11-24"]
    assert [s["lateDays"] for s in custom["schedule"]] == [0, 2, 3]
    dl = opt(r, "deadline")
    assert [s["name"] for s in dl["schedule"]] == ["Data pull", "VP overview", "Report"]
    assert [s["lateDays"] for s in dl["schedule"]] == [0, 0, 1] and dl["weightedLateness"] == 4
    st = opt(r, "stakeholder")
    assert [s["name"] for s in st["schedule"]] == ["VP overview", "Report", "Data pull"]
    assert st["schedule"][2]["lateDays"] == 4 and st["weightedLateness"] == 16
    assert opt(r, "impact")["order"] == dl["order"] and "deadline" in opt(r, "impact")["sameAs"]
    assert r["lowestRiskKey"] == "deadline"
    assert priorities.compute(INPUTS) == r  # deterministic


def test_everything_fits_with_more_time():
    r = priorities.compute({**INPUTS, "committedHours": 0})  # 8 h a day
    assert r["fits"] is True and opt(r, "deadline")["lateCount"] == 0
    assert "on time" in opt(r, "deadline")["risks"][0]["text"]


def test_list_validation_and_cross_field_rule():
    qs = packs.get_situation("competing-priorities")["questions"]
    _, errs = validate_answers(qs, {**INPUTS, "tasks": [TASKS[0]]})
    assert errs["tasks"] == "Add at least 2"
    bad_row = {**TASKS[1], "effortHours": -3, "requester": "ceo"}
    _, errs = validate_answers(qs, {**INPUTS, "tasks": [TASKS[0], bad_row]})
    assert set(errs) == {"tasks.1.effortHours", "tasks.1.requester"}
    _, errs = validate_answers(qs, {**INPUTS, "tasks": TASKS + [{"name": "", "effortHours": "", "deadline": ""}]})
    assert errs == {}  # an empty trailing row is ignored
    assert set(priorities.check({**INPUTS, "committedHours": 40})) == {"committedHours"}
    assert priorities.check(INPUTS) == {}


def test_priorities_flow_through_api(client):
    client.post("/api/auth/register", json={"email": "prio@example.com", "password": "correct-horse"})
    client.put("/api/profile", json={"roleId": "it-pm", "industry": "", "tenure": "1-3m", "fears": []})
    body = {"situationId": "competing-priorities", "privacyAck": True, "confidenceBefore": 2, "inputs": {**INPUTS, "committedHours": 40}}
    bad = client.post("/api/cases", json=body)
    assert bad.status_code == 400 and "committedHours" in bad.json()["fields"]
    made = client.post("/api/cases", json={**body, "inputs": INPUTS}).json()["case"]
    assert made["title"] == "Three asks" and len(made["result"]["options"]) == 4
    assert client.post(f"/api/cases/{made['id']}/decision", json={"option": "accept"}).status_code == 400  # not an option here
    case = client.post(f"/api/cases/{made['id']}/decision", json={"option": "custom", "rationale": "VP asked informally"}).json()["case"]
    assert case["document"].startswith("# Priority proposal: Three asks") and "What I need from you" in case["document"]
    assert case["debrief"]["points"][0].startswith("On your numbers")
    assert client.post(f"/api/cases/{made['id']}/hint", json={}).status_code in (404, 409)
    lib = client.get("/api/documents").json()["documents"]
    assert lib[0]["label"] == "Priority proposal" and lib[0]["caseTitle"] == "Three asks"
    assert client.get("/api/journal").json()["cases"][0]["title"] == "Three asks"
    public = {s["id"]: s for s in client.get("/api/packs").json()["situations"]}
    story = public["competing-priorities"]["storylines"][0]["answers"]["tasks"][0]["deadline"]
    assert len(story) == 10 and story > packs.today()  # storyline dates resolve to real dates
