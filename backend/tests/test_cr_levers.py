"""Change request: time, money and quality of accept, accept part, defer and decline; and what went into each risk label. Numbers by hand."""
from app import engine, packs
from app.document import build_document

SIT = packs.get_situation("client-change-request")
BASE = dict(asOf="2026-11-16", releaseDate="2026-11-30", teamSize=6, dailyRate=600, budgetRemaining=40000, changeEffortDays=10, bufferDays=2,
            clientCoversPct=0, delayPenaltyPerDay=0, overheadPct=25, parallelPct=60, focusPct=70, priority="important", changeTitle="Export", requestedBy="Jo")


def row(r, k):
    return next(x for x in r["levers"] if x["key"] == k)


def test_four_rows_by_hand_with_a_partial_share():
    r = engine.run(SIT, {**BASE, "partlyPct": 60})
    assert [x["key"] for x in r["levers"]] == ["accept", "partly", "defer", "decline"]
    a = row(r, "accept")  # 12.5 person-days -> 9 working days, 2 in the buffer -> 7 late, 7500 + 25200
    assert a["time"] == {"slipDays": 7, "date": "2026-12-09"} and a["money"]["total"] == 32700 and a["quality"]["deliveredPct"] == 100
    assert a["payWith"] == ["time", "money"]
    p = row(r, "partly")  # 6 person-days, 7.5 with overhead -> ceil(7.5 * 0.5 / 0.7) = 6 days, 4 late, 4500 + 4 * 6 * 600
    assert p["time"] == {"slipDays": 4, "date": "2026-12-04"} and p["money"]["total"] == 18900
    assert p["quality"] == {"cutShare": 0.4, "risk": "high", "deliveredPct": 60} and p["payWith"] == ["time", "money", "quality"]
    d = row(r, "defer")  # 1 person-day to re-plan (600) now, the 7500 work later
    assert d["time"]["slipDays"] == 0 and d["money"]["total"] == 8100 and d["money"]["later"] == 7500 and d["payWith"] == ["money", "goodwill"]
    n = row(r, "decline")
    assert n["money"]["total"] == 0 and n["payWith"] == ["goodwill"] and n["quality"]["deliveredPct"] == 0


def test_partial_share_not_set_says_so_instead_of_inventing_numbers():
    r = engine.run(SIT, BASE)
    p = row(r, "partly")
    assert p["time"] is None and p["money"]["total"] is None and p["money"]["notSet"] and p["quality"]["deliveredPct"] is None
    assert row(r, "accept")["money"]["total"] == 32700  # the other rows do not depend on it


def test_penalty_exposure_is_shown_and_a_nice_to_have_costs_no_goodwill():
    r = engine.run(SIT, {**BASE, "delayPenaltyPerDay": 1000, "priority": "nice", "partlyPct": 50})
    assert row(r, "accept")["money"]["penalty"] == 7000 and row(r, "partly")["money"]["penalty"] == 1000 * row(r, "partly")["time"]["slipDays"]
    assert "goodwill" not in row(r, "defer")["payWith"] and row(r, "decline")["payWith"] == []


def test_label_basis_says_what_counted_and_what_did_not():
    r = engine.run(SIT, BASE)
    acc = next(o for o in r["options"] if o["key"] == "accept")
    by = {b["axis"]: b["text"] for b in acc["labelBasis"]}
    assert "4 points" in by["time"] and "slip over 5 days adds 3" in by["time"]  # 3 for the 7-day slip + 1 for the change being over 30% of the time left
    assert "1 points" in by["money"] and "Budget left afterwards: 7300" in by["money"]  # a client who pays nothing for a non-must change
    assert "1 points for regression risk" in by["quality"] and "up to 15% low, up to 35% medium" in by["quality"]
    dfr = next(o for o in r["options"] if o["key"] == "defer")
    assert {b["axis"]: b["text"] for b in dfr["labelBasis"]}["time"] == "Time: no points, the release date does not move."


def test_label_basis_for_other_scenarios_is_explicit_about_missing_inputs():
    prio = packs.get_situation("competing-priorities")
    tasks = [{"name": "A", "effortHours": 14, "deadline": "2026-11-23", "requester": "manager", "impact": "reputation", "note": ""},
             {"name": "B", "effortHours": 6, "deadline": "2026-11-18", "requester": "peer", "impact": "money", "note": ""}]
    i = {"title": "x", "context": "", "tasks": tasks, "hoursPerWeek": 40, "committedHours": 15, "asOf": "2026-11-16"}
    none = {b["axis"]: b["text"] for b in engine.run(prio, i)["options"][0]["labelBasis"]}
    assert "no costs were entered" in none["money"] and "no scope cut was entered" in none["quality"]
    tasks[0].update(costPerLateDay=100, minEffortHours=8)
    some = {b["axis"]: b["text"] for b in engine.run(prio, {**i, "tasks": tasks})["options"][0]["labelBasis"]}
    assert "do not change this label" in some["money"] and "does not change this label" in some["quality"]


def test_document_includes_the_table():
    r = engine.run(SIT, {**BASE, "partlyPct": 60})
    doc = build_document({**BASE, "partlyPct": 60}, r, "accept", "why", None, "a@b.c", "2026-11-16", "client-change-request", SIT)
    assert "## Ways to fix it and what each costs" in doc and "Accept part of it" in doc and "quality risk high" in doc
