"""Time, money and quality: ways to fix lateness, with hand-checked numbers. Empty optional fields change nothing."""
from app import engine, packs
from app.engine import priorities

BASE = {"title": "Asks", "context": "", "hoursPerWeek": 40, "committedHours": 15, "asOf": "2026-11-16",
        "tasks": [{"name": "Report", "effortHours": 14, "deadline": "2026-11-23", "requester": "manager", "impact": "reputation", "note": ""},
                  {"name": "Data pull", "effortHours": 6, "deadline": "2026-11-18", "requester": "peer", "impact": "money", "note": ""},
                  {"name": "VP overview", "effortHours": 8, "deadline": "2026-11-19", "requester": "skip", "impact": "reputation", "note": ""}]}
SIT = packs.get_situation("competing-priorities")


def lv(r, key):
    return next(x for x in r["levers"] if x["key"] == key)


def test_no_optional_data_means_exactly_the_old_result():
    r = engine.run(SIT, BASE)
    assert "levers" not in r
    assert engine.run(SIT, {**BASE, "extraHourCost": 0, "extraHoursPerWeek": 0}) == r  # zero is "not entered"


def test_priorities_three_axes_by_hand():
    tasks = [{**t} for t in BASE["tasks"]]
    tasks[0].update(costPerLateDay=100, minEffortHours=8)  # the report: 14 h, minimum 8 h, 100 per day late
    i = {**BASE, "tasks": tasks, "extraHourCost": 30, "extraHoursPerWeek": 10}
    r = engine.run(SIT, i)
    # free 25 h a week = 5 h a day. Earliest deadline first: data pull 6 h -> 11-17, VP 8 h -> 11-18... report 12 h -> 11-23 vs deadline 11-19: late 2 days
    base = lv(r, "base")
    assert base["time"] == {"lateCount": 1, "lateDays": 2} or base["time"]["lateCount"] == 1
    assert base["money"]["late"] == base["time"]["lateDays"] * 100  # late days x cost per day
    # cut scope: the report goes to 8 h, cutting 6 of 28 h = 21.4 %: medium quality risk, nothing late
    sc = lv(r, "scope")
    assert sc["time"]["lateCount"] == 0 and sc["quality"]["reducedTasks"] == 1 and sc["quality"]["cutShare"] == round(6 / 28, 3) and sc["quality"]["risk"] == "medium"
    assert "quality" in sc["payWith"] and sc["money"]["total"] == 0
    # pay: the smallest number of extra hours a week that removes lateness, at 30 each over the working days it takes
    pay = lv(r, "pay")
    assert pay["time"]["lateCount"] == 0 and 1 <= pay["extraPerWeek"] <= 10 and pay["money"]["extra"] == round(pay["extraHours"] * 30)
    mv = lv(r, "move")
    assert mv["moves"] == [{"name": "Report", "days": base["time"]["lateDays"]}] and mv["payWith"] == ["goodwill"]


def test_quality_thresholds_and_validation():
    from app.levers import quality_risk
    assert [quality_risk(x) for x in (0.0, 0.15, 0.151, 0.35, 0.351)] == ["low", "low", "medium", "medium", "high"]
    bad = [{**t} for t in BASE["tasks"]]
    bad[1]["minEffortHours"] = 9  # more than the 6 hours of the task
    assert list(priorities.check({**BASE, "tasks": bad})) == ["tasks.1.minEffortHours"]
    assert priorities.check(BASE) == {}


def test_estimate_good_enough_and_pay_to_speed_up():
    sit = packs.get_situation("asked-for-a-deadline")
    e = {"title": "x", "context": "", "optimisticHours": 8, "likelyHours": 16, "pessimisticHours": 40, "hoursPerWeek": 20, "interruptionsPct": 20,
         "startDate": "2026-11-16", "requester": "manager", "costOfLate": "medium", "askedDeadline": "", "asOf": "2026-11-16"}
    assert "levers" not in engine.run(sit, e)
    r = engine.run(sit, {**e, "goodEnoughPct": 70, "hourlyCost": 40, "extraHoursPerWeek": 5})
    assert [x["key"] for x in r["levers"]] == ["base", "goodEnough", "pay"] and lv(r, "base")["date"] == "2026-11-26"
    ge = lv(r, "goodEnough")  # 70 % of 25.49 safe hours = 17.8 h -> ceil(17.8 / 3.2) = 6 days -> 2026-11-24
    assert ge["days"] == 6 and ge["date"] == "2026-11-24" and ge["quality"]["cutShare"] == 0.3 and ge["quality"]["risk"] == "medium" and ge["payWith"] == ["quality"]
    pay = lv(r, "pay")  # 25 h a week * 0.8 = 4 h a day -> ceil(25.49 / 4) = 7 days -> 2026-11-25; 1 h a day x 7 days x 40 = 280
    assert pay["days"] == 7 and pay["date"] == "2026-11-25" and pay["extraHours"] == 7 and pay["money"]["total"] == 280


def test_document_shows_the_three_axes_only_with_money_data():
    from app.document import build_document
    r0 = engine.run(SIT, BASE)
    assert "Ways to fix it" not in build_document(BASE, r0, "deadline", "why", None, "a@b.c", "2026-11-16", "competing-priorities", SIT)
    tasks = [{**t} for t in BASE["tasks"]]; tasks[0].update(costPerLateDay=100, minEffortHours=8)
    i = {**BASE, "tasks": tasks, "extraHourCost": 30, "extraHoursPerWeek": 10}
    doc = build_document(i, engine.run(SIT, i), "deadline", "why", None, "a@b.c", "2026-11-16", "competing-priorities", SIT)
    assert "## Ways to fix it and what each costs" in doc and "Cut scope on the late tasks" in doc and "quality risk medium" in doc
