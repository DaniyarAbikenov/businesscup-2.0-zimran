# -*- coding: utf-8 -*-
"""Predict first, then reveal: scores by hand, skipped guess, validation, the fewer-than-3 rule and isolation."""
import re

import pytest

from app import engine, packs, prediction
from app.errors import ApiError
from test_api import signup

PRIO = {"title": "Three asks", "context": "", "hoursPerWeek": 40, "committedHours": 15, "asOf": "2026-11-16",
        "tasks": [{"name": "Report", "effortHours": 14, "deadline": "2026-11-23", "requester": "manager", "impact": "reputation", "note": ""},
                  {"name": "Data pull", "effortHours": 6, "deadline": "2026-11-18", "requester": "peer", "impact": "money", "note": ""},
                  {"name": "VP overview", "effortHours": 8, "deadline": "2026-11-19", "requester": "skip", "impact": "reputation", "note": ""}]}
EST = {"title": "Churn report", "context": "", "optimisticHours": 8, "likelyHours": 16, "pessimisticHours": 40, "hoursPerWeek": 20, "interruptionsPct": 20,
       "startDate": "2026-11-16", "requester": "manager", "costOfLate": "medium", "askedDeadline": "", "asOf": "2026-11-16"}
DEC = {"title": "Pick", "context": "", "criteria": [{"name": "Price", "weight": 5}, {"name": "Fit", "weight": 3}, {"name": "Risk", "weight": 2}],
       "options": [{"name": "A", "note": "", "s1": 4, "s2": 3, "s3": 2}, {"name": "B", "note": "", "s1": 3, "s2": 5, "s3": 4}, {"name": "C", "note": "", "s1": 5, "s2": 2, "s3": 3}],
       "reversibility": "costly", "whoAffected": "team", "confidence": "medium", "asOf": "2026-11-16"}


def sc(sid, inputs, guess):
    sit = packs.get_situation(sid)
    return prediction.score(sit, prediction.clean(sit, inputs, guess), engine.run(sit, inputs), inputs)


def test_priorities_scores_by_hand():
    # your own order finishes at 11-19, 11-20, 11-24: 2 tasks late (deadlines 11-23, 11-18, 11-19 -> late 0, 2, 3? = 2 late); lowest risk is "deadline"
    full = sc("competing-priorities", PRIO, {"lateCount": 2, "bestOrder": "deadline"})
    assert [p["hit"] for p in full["parts"]] == [True, True] and full["overall"] == 1.0
    half = sc("competing-priorities", PRIO, {"lateCount": 2, "bestOrder": "custom"})
    assert [p["hit"] for p in half["parts"]] == [True, False] and half["overall"] == 0.5
    off = sc("competing-priorities", PRIO, {"lateCount": 0, "bestOrder": "impact"})
    assert off["parts"][0]["error"] == -2 and off["overall"] == 0.0


def test_estimate_error_in_working_days():
    safe = "2026-11-26"  # Thursday: 8 working days from Monday 11-16 at 3.2 real hours a day
    assert engine.run(packs.get_situation("asked-for-a-deadline"), EST)["options"][2]["date"] == safe
    for guess, err, overall in (("2026-11-26", 0, 1.0), ("2026-11-27", 1, 1.0), ("2026-11-30", 2, 0.5), ("2026-11-23", -3, 0.5), ("2026-11-19", -5, 0.0)):
        s = sc("asked-for-a-deadline", EST, {"date": guess})
        assert s["parts"][0]["error"] == err and s["overall"] == overall, guess
    assert sc("asked-for-a-deadline", EST, {"date": "2026-11-27"})["parts"][0]["hit"] is True and sc("asked-for-a-deadline", EST, {"date": "2026-11-30"})["parts"][0]["hit"] is False


def test_decision_hit_and_miss_and_skipped():
    assert sc("choose-between-options", DEC, {"winner": 1})["overall"] == 1.0  # B scores 76 against 74 and 66
    assert sc("choose-between-options", DEC, {"winner": 2})["overall"] == 0.0
    assert sc("choose-between-options", DEC, None) is None  # skipped: nothing stored, nothing scored
    assert prediction.clean(packs.get_situation("client-change-request"), {}, {"anything": 1}) is None  # change requests have no guess step


def test_validation_of_the_payload():
    sit = packs.get_situation("competing-priorities")
    for bad in ("x", {"lateCount": 9, "bestOrder": "deadline"}, {"lateCount": True, "bestOrder": "deadline"}, {"lateCount": 1, "bestOrder": "nope"}, {"lateCount": -1, "bestOrder": "custom"}):
        with pytest.raises(ApiError) as e:
            prediction.clean(sit, PRIO, bad)
        assert e.value.status == 400
    est = packs.get_situation("asked-for-a-deadline")
    for bad in ({"date": "tomorrow"}, {"date": "2026-02-30"}, {"date": "2020-01-01"}, {"date": "2030-01-01"}, {"date": "2026-11-20", "confidence": 120}):
        with pytest.raises(ApiError):
            prediction.clean(est, EST, bad)
    assert prediction.clean(est, EST, {"date": "2026-11-20", "confidence": 70}) == {"date": "2026-11-20", "confidence": 70}
    with pytest.raises(ApiError):
        prediction.clean(packs.get_situation("choose-between-options"), DEC, {"winner": 3})


def make(client, guess, lang="en", title="Asks"):
    body = {"situationId": "competing-priorities", "privacyAck": True, "confidenceBefore": 3, "inputs": {
        "title": title, "context": "", "hoursPerWeek": 40, "committedHours": 15,
        "tasks": [{"name": "A", "effortHours": 14, "deadline": "2030-01-23", "requester": "manager", "impact": "reputation", "note": ""},
                  {"name": "B", "effortHours": 6, "deadline": "2030-01-18", "requester": "peer", "impact": "money", "note": ""}]}}
    if guess is not None:
        body["prediction"] = guess
    return client.post("/api/cases", json=body, headers={"x-lang": lang})


def test_api_flow_reveal_trend_rule_and_isolation(client, make_client, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "FREE_CASES", 99)  # the free plan allows 3 scenarios; this test makes five
    signup(client, "pred@example.com")
    client.put("/api/profile", json={"roleId": "promoted-to-lead", "industry": "", "tenure": "1-3m", "fears": []})
    bad = make(client, {"lateCount": 7, "bestOrder": "deadline"})
    assert bad.status_code == 400 and "prediction.lateCount" in bad.json()["fields"]
    assert client.post("/api/cases/check", json={"situationId": "competing-priorities", "inputs": {"title": "x"}}).status_code == 400
    ok = client.post("/api/cases/check", json={"situationId": "competing-priorities", "inputs": make.__defaults__ and {"title": "x", "hoursPerWeek": 40, "committedHours": 15,
        "tasks": [{"name": "A", "effortHours": 14, "deadline": "2030-01-23", "requester": "manager", "impact": "reputation", "note": ""}, {"name": "B", "effortHours": 6, "deadline": "2030-01-18", "requester": "peer", "impact": "money", "note": ""}]}}).json()
    assert ok["engine"] == "priorities" and ok["preview"]["tasks"] == 2 and len(ok["preview"]["orders"]) == 4
    skipped = make(client, None).json()["case"]
    assert skipped["prediction"] is None
    first = make(client, {"lateCount": 0, "bestOrder": "deadline"}).json()["case"]
    assert first["prediction"]["items"][0]["label"].startswith("Tasks that finish late") and first["prediction"]["overall"] in (0.0, 0.5, 1.0)
    prog = client.get("/api/progress").json()
    pr = next(s for s in prog["skills"] if s["key"] == "prioritising")
    assert pr["cases"] == 2 and pr["guesses"] == 1 and pr["enough"] is False and pr["hitRate"] is None and pr["ticks"] == []  # fewer than 3 guesses: no trend, no percentage
    make(client, {"lateCount": 0, "bestOrder": "deadline"})
    assert next(s for s in client.get("/api/progress").json()["skills"] if s["key"] == "prioritising")["hitRate"] is None
    third = make(client, {"lateCount": 0, "bestOrder": "deadline"}).json()["case"]
    pr = next(s for s in client.get("/api/progress").json()["skills"] if s["key"] == "prioritising")
    assert pr["enough"] is True and pr["guesses"] == 3 and len(pr["ticks"]) == 3 and 0 <= pr["hitRate"] <= 100
    assert pr["hitRate"] == round(100 * sum(pr["ticks"]) / 3)  # the server computes it, from the stored scores
    tl = client.get("/api/progress").json()["timeline"]
    assert any(t["guess"] and t["guess"]["parts"] == 2 for t in tl)
    # Russian: the reveal text is in Russian, the stored score is the same
    ru = client.get(f"/api/cases/{third['id']}", headers={"x-lang": "ru"}).json()["case"]["prediction"]
    assert re.search("[А-Яа-я]", ru["sentence"]) and re.search("[А-Яа-я]", ru["items"][0]["label"]) and ru["overall"] == third["prediction"]["overall"]
    # another person sees nothing of this
    other = make_client()
    signup(other, "pred2@example.com")
    other.put("/api/profile", json={"roleId": "director", "industry": "", "tenure": "1-3m", "fears": []})
    assert all(s["guesses"] == 0 for s in other.get("/api/progress").json()["skills"])
    assert other.get(f"/api/cases/{third['id']}").status_code == 404


def test_demo_account_shows_a_trend_labelled_as_sample_data(client):
    r = client.post("/api/auth/demo", json={})
    assert r.status_code in (200, 201), r.text
    skills = {s["key"]: s for s in client.get("/api/progress").json()["skills"]}
    for key in ("prioritising", "estimating"):
        assert skills[key]["guesses"] == 3 and skills[key]["enough"] and skills[key]["ticks"][0] < skills[key]["ticks"][-1]  # far off first, closer later
    assert skills["choosing"]["guesses"] == 2 and skills["choosing"]["hitRate"] is None  # two guesses: still no trend
    me = client.get("/api/me").json()
    assert me["isDemo"] is True
