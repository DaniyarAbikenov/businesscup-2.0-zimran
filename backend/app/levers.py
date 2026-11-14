"""Time, money and quality together. The orders and dates show TIME; when the person enters optional money and scope data, this adds
ways to fix lateness, each recomputed by the same engine and scored on three axes. All of it is a rule on the person's own inputs,
not a measurement.

Priorities (base: the lowest-risk order):
  scope   tasks that finish late use their minimum acceptable hours (minEffortHours), largest saving first (a task's quality
          loss per hour saved is 1 / its hours), until nothing is late or no reduction is left
  pay     extra hours a week (up to extraHoursPerWeek, step 1) at extraHourCost until nothing is late
  move    the base order, and which deadlines would have to move and by how many working days
  money   late cost = late working days x costPerLateDay (summed) plus extra hours x extraHourCost
  quality cut share = hours cut / all hours; <= 15 % low, <= 35 % medium, more high
Estimate (base: the safe date): good enough (hours x goodEnoughPct) and pay to speed up (extraHoursPerWeek at hourlyCost).
Nothing is added when none of the optional fields is filled in, so existing results stay exactly as they were."""
import copy

from . import engine
from .engine.change_request import rnd
from .msg import tr


def _compute(sit, i):
    return engine.ENGINES[sit["engine"]].compute(i)  # the engine itself, not engine.run (which adds these)


def quality_risk(cut_share: float) -> str:
    return "low" if cut_share <= 0.15 else "medium" if cut_share <= 0.35 else "high"


def _best(result):
    return next(o for o in result["options"] if o["key"] == result["lowestRiskKey"])


def _late_cost(sched, tasks):
    if not any(t.get("costPerLateDay") for t in tasks):
        return None
    return sum(s["lateDays"] * (tasks[s["index"]].get("costPerLateDay") or 0) for s in sched)


def _axes(sched, tasks, extra_hours=0, extra_cost_rate=None, cut_hours=0, total_hours=1, reduced=0, label_pay=None):
    late = _late_cost(sched, tasks)
    extra = rnd(extra_hours * extra_cost_rate) if extra_cost_rate else (0 if extra_hours == 0 else None)
    money = None if (late is None and extra is None) else rnd((late or 0) + (extra or 0))
    share = cut_hours / total_hours if total_hours else 0
    pays = []
    if sum(s["lateDays"] for s in sched):
        pays.append("time")
    if (extra or 0) > 0 or (late or 0) > 0:
        pays.append("money")
    if cut_hours > 0:
        pays.append("quality")
    return {"time": {"lateCount": sum(1 for s in sched if s["lateDays"]), "lateDays": sum(s["lateDays"] for s in sched)},
            "money": {"late": None if late is None else rnd(late), "extra": extra, "total": money},
            "quality": {"reducedTasks": reduced, "cutShare": round(share, 3), "risk": quality_risk(share) if cut_hours else "low"},
            "payWith": pays, "extraHours": rnd(extra_hours, 1)}


def _priorities(sit, i, result):
    tasks = i["tasks"]
    has_min = any((t.get("minEffortHours") or 0) > 0 for t in tasks)
    pay_cap = i.get("extraHoursPerWeek") or 0
    rate = i.get("extraHourCost") or 0
    any_cost = any(t.get("costPerLateDay") for t in tasks)
    if not (has_min or pay_cap or rate or any_cost):
        return None
    base = _best(result)
    order = base["order"]
    total = sum(t["effortHours"] for t in tasks)
    out = []
    a = _axes(base["schedule"], tasks, total_hours=total)
    out.append({"key": "base", "label": tr("Best order, no changes"), **a, "note": tr("The lowest-risk order as it is.")})

    if has_min and base["lateCount"]:
        t2 = copy.deepcopy(tasks); cut = 0.0; reduced = 0
        while True:
            r = _compute(sit, {**i, "tasks": t2}); b = next(o for o in r["options"] if o["key"] == "custom")
            sched = next(o for o in r["options"] if o["key"] == base["key"])["schedule"]
            late_idx = [s["index"] for s in sched if s["lateDays"]]
            cand = [k for k in late_idx if (t2[k].get("minEffortHours") or 0) > 0 and t2[k]["minEffortHours"] < t2[k]["effortHours"]]
            if not late_idx or not cand:
                break
            k = max(cand, key=lambda x: t2[x]["effortHours"])
            cut += t2[k]["effortHours"] - t2[k]["minEffortHours"]; reduced += 1
            t2[k]["effortHours"] = t2[k]["minEffortHours"]
        r = _compute(sit, {**i, "tasks": t2})
        sched = next(o for o in r["options"] if o["key"] == base["key"])["schedule"]
        out.append({"key": "scope", "label": tr("Cut scope on the late tasks"), **_axes(sched, tasks, cut_hours=cut, total_hours=total, reduced=reduced),
                    "note": tr("Tasks that would be late are delivered in their minimum version.")})

    if pay_cap and base["lateCount"]:
        used = 0
        for extra in range(1, int(pay_cap) + 1):
            used = extra
            r = _compute(sit, {**i, "hoursPerWeek": i["hoursPerWeek"] + extra})
            sched = next(o for o in r["options"] if o["key"] == base["key"])["schedule"]
            if not any(s["lateDays"] for s in sched):
                break
        days = max(1, round(total / max(0.5, r["freeHoursPerDay"])))
        out.append({"key": "pay", "label": tr("Pay for extra hours"), **_axes(sched, tasks, extra_hours=used / 5 * days, extra_cost_rate=rate or None, total_hours=total),
                    "extraPerWeek": used, "note": tr("{n} extra hours a week.", n=used)})

    late = [s for s in base["schedule"] if s["lateDays"]]
    if late:
        out.append({"key": "move", "label": tr("Ask to move a deadline"), **_axes([{**s, "lateDays": 0} for s in base["schedule"]], tasks, total_hours=total),
                    "moves": [{"name": s["name"], "days": s["lateDays"]} for s in late],
                    "note": tr("Deadlines to move: {list}.", list=", ".join(f"{s['name']} ({s['lateDays']})" for s in late))})
        out[-1]["payWith"] = ["goodwill"]
    return out


def _estimate(sit, i, result):
    pct = i.get("goodEnoughPct") or 0
    extra = i.get("extraHoursPerWeek") or 0
    rate = i.get("hourlyCost") or 0
    if not (pct or extra or rate):
        return None
    safe = next(o for o in result["options"] if o["key"] == "safe")
    out = [{"key": "base", "label": tr("Safe date as it is"), "date": safe["date"], "days": safe["workdays"], "money": {"total": 0}, "quality": {"cutShare": 0, "risk": "low"},
            "payWith": [], "note": tr("The safe date from your estimate.")}]
    if 0 < pct < 100:
        v = copy.deepcopy(i)
        for k in ("optimisticHours", "likelyHours", "pessimisticHours"):
            v[k] = round(i[k] * pct / 100, 2)
        s = next(o for o in _compute(sit, v)["options"] if o["key"] == "safe")
        share = 1 - pct / 100
        out.append({"key": "goodEnough", "label": tr("Deliver the good-enough version"), "date": s["date"], "days": s["workdays"], "money": {"total": 0},
                    "quality": {"cutShare": round(share, 3), "risk": quality_risk(share)}, "payWith": ["quality"],
                    "note": tr("{pct}% of the hours: agree what is left out.", pct=pct)})
    if extra:
        v = {**i, "hoursPerWeek": min(80, i["hoursPerWeek"] + extra)}
        r = _compute(sit, v)
        s = next(o for o in r["options"] if o["key"] == "safe")
        hours = extra / 5 * s["workdays"]
        out.append({"key": "pay", "label": tr("Pay to speed up"), "date": s["date"], "days": s["workdays"], "money": {"total": rnd(hours * rate) if rate else None},
                    "quality": {"cutShare": 0, "risk": "low"}, "payWith": ["money"] if rate else ["money"], "extraHours": rnd(hours, 1),
                    "note": tr("{n} extra hours a week.", n=extra)})
    return out


def compute(sit: dict, i: dict, result: dict):
    if sit["engine"] == "priorities":
        return _priorities(sit, i, result)
    if sit["engine"] == "estimate":
        return _estimate(sit, i, result)
    return None
