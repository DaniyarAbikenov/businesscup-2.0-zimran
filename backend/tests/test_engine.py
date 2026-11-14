from app.engine.change_request import add_workdays, compute, workdays_between
from app.packs import situations
from app.validate import validate_answers

base = dict(
    asOf="2026-11-16", releaseDate="2026-11-30", teamSize=6, dailyRate=600, budgetRemaining=40000,
    changeEffortDays=10, bufferDays=2, clientCoversPct=0, delayPenaltyPerDay=0,
    overheadPct=25, parallelPct=60, focusPct=70, priority="important",
)


def opt(r, k):
    return next(o for o in r["options"] if o["key"] == k)


def test_workday_math_skips_weekends():
    assert workdays_between("2026-11-16", "2026-11-30") == 10
    assert workdays_between("2026-11-20", "2026-11-23") == 1  # Fri -> Mon
    assert add_workdays("2026-11-27", 1) == "2026-11-30"
    assert add_workdays("2026-11-30", 7) == "2026-12-09"


def test_accept_slip_cost_and_budget():
    r = compute(base)
    a = opt(r, "accept")
    # 10 * 1.25 = 12.5 person-days; (0.4 + 0.6/6) / 0.7 * 12.5 = 8.93 -> 9 working days
    assert r["totalChangeDays"] == 12.5
    assert a["addedWorkdays"] == 9
    assert a["slipWorkdays"] == 7  # 9 - 2 buffer
    assert a["newReleaseDate"] == "2026-12-09"
    assert a["costBreakdown"]["labor"] == 7500
    assert a["costBreakdown"]["extendedRun"] == 25200
    assert a["extraCost"] == 32700
    assert a["budgetAfter"] == 7300
    assert a["riskLevel"] == "high"


def test_accept_inside_buffer_keeps_date():
    a = opt(compute({**base, "changeEffortDays": 1, "bufferDays": 5}), "accept")
    assert a["slipWorkdays"] == 0 and a["newReleaseDate"] == base["releaseDate"] and a["bufferLeft"] == 4


def test_client_funding_and_penalty():
    a = opt(compute({**base, "clientCoversPct": 100, "delayPenaltyPerDay": 1000}), "accept")
    assert a["costBreakdown"]["delayPenalty"] == 7000
    assert a["costBreakdown"]["clientCovers"] == 7500
    assert a["extraCost"] == 7500 + 25200 + 7000 - 7500


def test_budget_overrun_flagged():
    a = opt(compute({**base, "budgetRemaining": 5000}), "accept")
    assert a["budgetAfter"] < 0 and any("overrun" in r["text"].lower() for r in a["risks"])


def test_defer_decline_follow_priority():
    must, nice = compute({**base, "priority": "must"}), compute({**base, "priority": "nice"})
    assert opt(must, "defer")["newReleaseDate"] == base["releaseDate"]
    assert opt(must, "decline")["extraCost"] == 0 and opt(must, "decline")["riskLevel"] == "high"
    assert opt(nice, "defer")["riskLevel"] == "low" and opt(nice, "decline")["riskLevel"] == "low"
    assert opt(nice, "defer")["laterCost"] == 7500


def test_deterministic():
    assert compute(base) == compute(dict(base))


def test_validation():
    q = situations[0]["questions"]
    _, errors = validate_answers(q, {"teamSize": 0, "releaseDate": "soon", "priority": "huge", "dailyRate": "abc"})
    assert {"teamSize", "releaseDate", "priority", "dailyRate", "changeTitle"} <= set(errors)
    values, errors = validate_answers(q, {
        "changeTitle": "Add export", "requestedBy": "Client", "priority": "nice", "releaseDate": "2026-12-01",
        "teamSize": "5", "dailyRate": "500", "budgetRemaining": "10,000", "changeEffortDays": 3, "bufferDays": 1,
        "clientCoversPct": 0, "overheadPct": 25, "parallelPct": 60, "focusPct": 70})
    assert not errors and values["budgetRemaining"] == 10000
