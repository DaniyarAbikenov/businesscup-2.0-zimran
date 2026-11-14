"""Deterministic impact calculation for a late client change request.
No LLM involved: the same inputs always give the same numbers."""
import math
from datetime import date, timedelta


def rnd(n: float, p: int = 0):
    """Round half up (not banker's rounding), so results match what people expect."""
    f = 10 ** p
    v = math.floor(n * f + 0.5) / f
    return int(v) if p == 0 else v


def fmt(n: float) -> str:
    return f"{rnd(n):,}"


def workdays_between(frm: str, to: str) -> int:
    """Working days in (from, to]; negative if `to` is before `from`."""
    a, b = date.fromisoformat(frm), date.fromisoformat(to)
    if b < a:
        return -workdays_between(to, frm)
    n, d = 0, a
    while d < b:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def add_workdays(frm: str, n: int) -> str:
    d, left = date.fromisoformat(frm), n
    while left > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            left -= 1
    return d.isoformat()


def level_of(score: int) -> str:
    return "high" if score >= 4 else "medium" if score >= 2 else "low"


def compute(i: dict) -> dict:
    workdays_to_release = workdays_between(i["asOf"], i["releaseDate"])
    overhead, parallel, focus = i["overheadPct"] / 100, i["parallelPct"] / 100, i["focusPct"] / 100

    # Effort including testing / coordination overhead.
    total_days = i["changeEffortDays"] * (1 + overhead)
    # Calendar time the change adds: the non-splittable part runs on one person, the splittable
    # part is shared across the team (Amdahl's law), at `focus` productivity.
    added = math.ceil(total_days * ((1 - parallel) + parallel / i["teamSize"]) / focus - 1e-9)
    slip = max(0, added - i["bufferDays"])
    buffer_left = max(0, i["bufferDays"] - added)

    # ---- Accept ----
    labor = total_days * i["dailyRate"]
    extended_run = slip * i["teamSize"] * i["dailyRate"]
    penalty = slip * i["delayPenaltyPerDay"]
    gross = labor + extended_run + penalty
    client_covers = labor * i["clientCoversPct"] / 100
    net = gross - client_covers
    budget_after = i["budgetRemaining"] - net
    new_date = add_workdays(i["releaseDate"], slip) if slip > 0 else i["releaseDate"]

    ar = []
    if slip > 5:
        ar.append((3, f"Release slips {slip} working days to {new_date}. Expect a hard conversation with the client."))
    elif slip > 0:
        ar.append((2, f"Release slips {slip} working day{'' if slip == 1 else 's'} to {new_date}."))
    elif i["bufferDays"] > 0 and added / i["bufferDays"] >= 0.7:
        ar.append((1, f"The change uses {added} of your {i['bufferDays']} buffer days. Almost no room for surprises."))
    if budget_after < 0:
        ar.append((3, f"Budget overrun of ${fmt(-budget_after)}. You need approval for more money."))
    elif i["budgetRemaining"] > 0 and budget_after < i["budgetRemaining"] * 0.15:
        ar.append((1, f"Only ${fmt(budget_after)} of budget left afterwards (under 15%)."))
    if workdays_to_release <= 10:
        ar.append((1, f"Only {workdays_to_release} working days to the release. Late changes carry extra regression risk."))
    if workdays_to_release > 0 and added > workdays_to_release * 0.3:
        ar.append((1, f"The change needs {added} working days, over 30% of the time left."))
    if i["clientCoversPct"] == 0 and i["priority"] != "must":
        ar.append((1, "The client pays nothing for this. Consider asking for a funded change order."))

    # ---- Defer ----
    planning = i["dailyRate"] * 1  # ~1 person-day to re-baseline, write it up and talk to the client
    dr = []
    if i["priority"] == "must":
        dr.append((4, "The client says this is a must-have. Deferring it likely blocks their launch."))
    elif i["priority"] == "important":
        dr.append((2, "Important to the client. They may push back or escalate."))
    else:
        dr.append((0, "Low relationship risk for a nice-to-have, as long as the next slot is dated."))
    dr.append((0, f"The work still costs about ${fmt(labor)} later ({rnd(total_days, 1)} person-days incl. overhead)."))

    # ---- Decline ----
    cr = []
    if i["priority"] == "must":
        cr.append((5, "Declining a must-have is rarely viable. Escalate to your manager first."))
    elif i["priority"] == "important":
        cr.append((3, "The client will feel unheard unless you offer an alternative."))
    else:
        cr.append((1, "Low risk for a nice-to-have if you explain the reason with dates and cost."))

    def mk(key, risks, **extra):
        score = sum(s for s, _ in risks)
        return {"key": key, "riskScore": score, "riskLevel": level_of(score),
                "risks": [{"severity": s, "text": t} for s, t in risks], **extra}

    options = [
        mk("accept", ar, newReleaseDate=new_date, slipWorkdays=slip, addedWorkdays=added, bufferLeft=buffer_left,
           extraCost=rnd(net), grossExtraCost=rnd(gross),
           costBreakdown={"labor": rnd(labor), "extendedRun": rnd(extended_run), "delayPenalty": rnd(penalty),
                          "clientCovers": rnd(client_covers)},
           budgetAfter=rnd(budget_after)),
        mk("defer", dr, newReleaseDate=i["releaseDate"], slipWorkdays=0, extraCost=rnd(planning),
           grossExtraCost=rnd(planning), laterCost=rnd(labor), budgetAfter=rnd(i["budgetRemaining"] - planning)),
        mk("decline", cr, newReleaseDate=i["releaseDate"], slipWorkdays=0, extraCost=0, grossExtraCost=0,
           budgetAfter=rnd(i["budgetRemaining"])),
    ]
    lowest = min(options, key=lambda o: o["riskScore"])  # stable: first wins on ties
    return {
        "asOf": i["asOf"],
        "workdaysToRelease": workdays_to_release,
        "totalChangeDays": rnd(total_days, 1),
        "addedWorkdays": added,
        "options": options,
        "lowestRiskKey": lowest["key"],
        "assumptions": (
            f"Effort {i['changeEffortDays']} person-days + {i['overheadPct']}% overhead = {rnd(total_days, 1)}. "
            f"{i['parallelPct']}% of it is split across {i['teamSize']} people at {i['focusPct']}% productivity, "
            f"which adds {added} working days. Weekends are skipped. Rates are your inputs."
        ),
    }
