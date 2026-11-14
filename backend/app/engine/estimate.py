"""Deterministic estimate-and-promise comparison for "I was asked when it will be done".

The person gives a three-point estimate (optimistic, likely, pessimistic hours), the hours a week they really
have free, and how much of that is lost to interruptions. Four things they could say are compared: the optimistic
date, the likely date, a safe date and a range with a check-in. No randomness, no LLM: same inputs, same numbers.

Formulas (PERT with a normal approximation):
  mean  = (optimistic + 4 * likely + pessimistic) / 6
  sd    = (pessimistic - optimistic) / 6
  hours per working day = free hours per week / 5 * (1 - interruptions / 100)
  working days needed for H hours = ceil(H / hours per working day), at least 1
  chance to make a date = Phi((days * hours per day - mean) / sd), Phi = standard normal CDF
  safe date = the date for mean + 1.28 * sd hours (about 90 % chance)
Risk points: missing the date (chance >= 85 % : 0, >= 65 % : 1, >= 45 % : 2, >= 25 % : 3, else 4), plus 1 to 2 when the
cost of being late is medium or high and the chance is under 65 % (plus 1 if the one asking is a client), plus 1 to 3
when the date is after the deadline they asked for (1-2 days : 1, 3-5 : 2, more : 3). A range with a check-in
removes one miss point, because you can warn early."""
from ..msg import tr
import math

from .change_request import add_workdays, level_of, rnd, workdays_between

Z_SAFE = 1.28
COST_BONUS = {"low": 0, "medium": 1, "high": 2}
REQUESTER = {"manager": "your manager", "client": "someone outside the organisation", "peer": "a colleague"}
COST_TEXT = {"low": "a late answer is a small inconvenience", "medium": "being late hurts trust or costs something",
             "high": "being late has serious consequences (contract, launch, money)"}
ORDER = ["optimistic", "likely", "safe", "range"]


def phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def check(i: dict) -> dict:
    """Rules that span several fields. Returns {field: message}."""
    errs = {}
    if i.get("hiddenHours", 0) >= i["hoursPerWeek"]:
        errs["hiddenHours"] = tr("Must be less than your free hours")
    if i["likelyHours"] < i["optimisticHours"]:
        errs["likelyHours"] = tr('Must not be less than the optimistic estimate')
    if i["pessimisticHours"] < i["likelyHours"]:
        errs["pessimisticHours"] = tr('Must not be less than the likely estimate')
    return errs


def _days(hours: float, per_day: float) -> int:
    return max(1, math.ceil(hours / per_day - 1e-9))


def compute(i: dict) -> dict:
    o, m, p = i["optimisticHours"], i["likelyHours"], i["pessimisticHours"]
    mean, sd = (o + 4 * m + p) / 6, (p - o) / 6
    per_day = max(0.5, i["hoursPerWeek"] - i.get("hiddenHours", 0)) / 5 * (1 - i["interruptionsPct"] / 100)
    start, asked = i["startDate"], i.get("askedDeadline") or ""
    cost, who = i["costOfLate"], i["requester"]

    def chance(days: int) -> float:
        cap = days * per_day
        return phi((cap - mean) / sd) if sd > 0 else (1.0 if cap >= mean - 1e-9 else 0.0)

    hours = {"optimistic": o, "likely": m, "safe": mean + Z_SAFE * sd}
    days = {k: _days(h, per_day) for k, h in hours.items()}
    days["range"] = days["safe"]
    recheck_days = _days(0.5 * m, per_day)
    recheck = add_workdays(start, recheck_days)
    options = []
    for key in ORDER:
        n = days[key]
        date = add_workdays(start, n)
        date_from = add_workdays(start, days["likely"]) if key == "range" else None
        pr = chance(n)
        late = max(0, workdays_between(asked, date)) if asked else 0
        pct = rnd(pr * 100)
        risks = []
        miss = 0 if pr >= .85 else 1 if pr >= .65 else 2 if pr >= .45 else 3 if pr >= .25 else 4
        if key == "range":
            miss = max(0, miss - 1)
        if miss:
            risks.append((miss, tr('About {pct}% chance to finish by {date}. That is {safe}: if it slips, {cost}.', pct=pct, date=date, safe=tr('less than even') if pr < 0.5 else tr('not safe'), cost=tr(COST_TEXT[cost]))))
        bonus = COST_BONUS[cost] + (1 if who == "client" else 0) if pr < .65 else 0
        if bonus:
            risks.append((bonus, tr('{capitalize} is asking and {cost}, so a missed date costs more here.', capitalize=tr(REQUESTER[who]).capitalize(), cost=tr(COST_TEXT[cost]))))
        if late:
            pts = 1 if late <= 2 else 2 if late <= 5 else 3
            risks.append((pts, tr('{date} is {late} working day{sfx} after the date they asked for ({asked}). Expect pushback; say what the date is based on and what could be cut.', date=date, late=late, sfx='s' if late != 1 else '', asked=asked)))
        if key == "range":
            risks.append((0, tr('A range is only useful with a check-in. Re-check on {recheck} (after about half of the likely work) and tell them then.', recheck=recheck)))
        if not [r for r in risks if r[0] > 0]:
            risks.append((0, tr('About {pct}% chance to make {date}, and it is not after the date they asked for.', pct=pct, date=date) if asked
                          else tr('About {pct}% chance to make {date}.', pct=pct, date=date)))
        score = sum(s for s, _ in risks)
        options.append({
            "key": key, "date": date, "dateFrom": date_from, "workdays": n, "hours": rnd(hours.get(key, hours["safe"]), 1),
            "probability": pct, "lateDays": late, "recheckDate": recheck if key == "range" else None,
            "riskScore": score, "riskLevel": level_of(score), "risks": [{"severity": s, "text": t} for s, t in risks],
        })
    best = min(options, key=lambda x: (x["riskScore"], x["lateDays"]))  # stable: list order wins ties
    safe = next(x for x in options if x["key"] == "safe")
    headline = (tr('You think {m:g} hours is most likely, but with the spread in your estimate the expected effort is {v:g} hours. At {v2:g} real hours a day, the likely date is {date} and the safe date (about 90 % chance) is {date2}.', m=m, v=rnd(mean, 1), v2=rnd(per_day, 1), date=next((x for x in options if x['key'] == 'likely'))['date'], date2=safe['date']))
    return {
        "engine": "estimate", "asOf": i["asOf"], "headline": headline, "meanHours": rnd(mean, 1), "sdHours": rnd(sd, 1),
        "hoursPerDay": rnd(per_day, 1), "askedDeadline": asked or None, "options": options, "lowestRiskKey": best["key"],
        "assumptions": (tr('Expected effort = (optimistic + 4 x likely + pessimistic) / 6 = {v} hours, spread (pessimistic - optimistic) / 6 = {v2} hours. You have {hoursPerWeek} free hours a week and lose {interruptionsPct}% to interruptions, so {v3} real hours a working day. Working days start on {start}, weekends are skipped. Chance to make a date = normal distribution with that mean and spread, at the hours available by that date. Safe date = mean + {Z_SAFE} x spread (about 90 %). These are rules of thumb, not a prediction.', v=rnd(mean, 1), v2=rnd(sd, 1), hoursPerWeek=i['hoursPerWeek'], interruptionsPct=i['interruptionsPct'], v3=rnd(per_day, 1), start=start, Z_SAFE=Z_SAFE)),
    }
