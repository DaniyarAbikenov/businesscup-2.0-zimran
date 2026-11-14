"""Stress tests on the user's own numbers. Not a forecast: it only asks "does the best option still win if my numbers are a bit worse?".
Per engine, two worse variants of the inputs are recomputed with the same deterministic engine; the answer says whether the
lowest-risk option stays the same and how far the risk moves."""
import copy

from . import engine
from .msg import tr

LEVEL = {"low": 0, "medium": 1, "high": 2}


def _variants(sit: dict, i: dict) -> list[tuple[str, dict]]:
    e = sit["engine"]
    out = []
    if e == "change_request":
        a = copy.deepcopy(i); a["changeEffortDays"] = round(i["changeEffortDays"] * 1.2, 2)
        b = copy.deepcopy(i); b["bufferDays"] = max(0, i["bufferDays"] - 1)
        out = [(tr("the effort for the change is 20% higher"), a), (tr("you have one working day less of buffer"), b)]
    elif e == "priorities":
        a = copy.deepcopy(i)
        for t in a["tasks"]:
            t["effortHours"] = round(t["effortHours"] * 1.2, 2)
        b = copy.deepcopy(i)
        if len(b["tasks"]) < 5:
            first = min(t["deadline"] for t in b["tasks"])
            b["tasks"].append({"name": tr("Unplanned task"), "effortHours": 4, "deadline": first, "requester": "peer", "impact": "minor", "note": ""})
        else:
            b["committedHours"] = min(b["hoursPerWeek"] - 1, b["committedHours"] + 4)
        out = [(tr("every estimate is 20% higher"), a), (tr("one unplanned 4-hour task lands before the first deadline"), b)]
    elif e == "estimate":
        a = copy.deepcopy(i)
        for k in ("optimisticHours", "likelyHours", "pessimisticHours"):
            a[k] = round(i[k] * 1.2, 2)
        b = copy.deepcopy(i); b["interruptionsPct"] = min(80, i["interruptionsPct"] + 10)
        out = [(tr("every estimate is 20% higher"), a), (tr("interruptions take 10 points more of your time"), b)]
    elif e == "decision":
        base = engine.run(sit, i)
        win = base["ranking"][0]["index"]; run = base["ranking"][1]["index"]
        a = copy.deepcopy(i)
        for k in range(len(i["criteria"])):
            key = f"s{k + 1}"; a["options"][win][key] = max(1, i["options"][win][key] - 1)
        b = copy.deepcopy(i)
        for k in range(len(i["criteria"])):
            key = f"s{k + 1}"; b["options"][run][key] = min(5, i["options"][run][key] + 1)
        out = [(tr("the leading option is one point worse on every criterion"), a), (tr("the runner-up is one point better on every criterion"), b)]
    return out


def run(sit: dict, inputs: dict, result: dict, labels: dict) -> list[dict]:
    """labels: option key -> label. Returns one entry per stress test."""
    base_best = result["lowestRiskKey"]
    base = next(o for o in result["options"] if o["key"] == base_best)
    out = []
    for what, variant in _variants(sit, inputs):
        try:
            res = engine.run(sit, variant)
        except Exception:  # a variant can leave the allowed ranges (for example no free hours left): that already means "it breaks"
            out.append({"what": what, "holds": False, "newBest": None, "text": tr("If {what}, the numbers no longer work at all. Your plan has no room for this.", what=what)})
            continue
        new_best = res["lowestRiskKey"]
        after = next(o for o in res["options"] if o["key"] == base_best)
        holds = new_best == base_best
        worse = LEVEL[after["riskLevel"]] > LEVEL[base["riskLevel"]]
        if holds and not worse:
            text = tr('If {what}, "{label}" is still the lowest-risk option ({level} risk).', what=what, label=labels[base_best], level=tr(after["riskLevel"] + " (risk)"))
        elif holds:
            text = tr('If {what}, "{label}" is still the best, but its risk goes from {before} to {after}.', what=what, label=labels[base_best], before=tr(base["riskLevel"] + " (risk)"), after=tr(after["riskLevel"] + " (risk)"))
        else:
            text = tr('If {what}, the best option changes: "{new}" would score lower risk than "{label}". Your conclusion does not hold.', what=what, new=labels[new_best], label=labels[base_best])
        out.append({"what": what, "holds": holds and not worse, "sameBest": holds, "newBest": new_best, "riskBefore": base["riskLevel"], "riskAfter": after["riskLevel"], "text": text})
    return out
