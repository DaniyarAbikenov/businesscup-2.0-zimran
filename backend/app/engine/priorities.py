"""Deterministic schedule comparison for competing priorities.

The user lists 2-5 tasks (effort, deadline, who asked, what happens if it is late) and how many hours
a week they really have. Each option is an order of work. Tasks run one after another at the user's free
capacity, on working days only, so every option shows when each task finishes and which ones are late.
No LLM involved: the same inputs always give the same numbers."""
import math

from .change_request import add_workdays, level_of, rnd, workdays_between

REQUESTER = {  # weight: how visible a miss is, and the label used in text
    "skip": (3, "your manager's manager"),
    "manager": (2, "your manager"),
    "client": (3, "a client"),
    "peer": (1, "a colleague"),
    "self": (0, "you"),
}
IMPACT = {  # weight: how much damage a miss does, and how it is described
    "blocks": (3, "it blocks other people's work"),
    "money": (3, "it costs money or a contract"),
    "reputation": (2, "it hurts trust in you or the team"),
    "minor": (1, "the impact is minor"),
}

STRATEGIES = {
    # key -> sort key over (index, task); Python's sort is stable, so ties keep the listed order
    "deadline": lambda it: (it[1]["deadline"],),
    "stakeholder": lambda it: (-REQUESTER[it[1]["requester"]][0], it[1]["deadline"]),
    "impact": lambda it: (-IMPACT[it[1]["impact"]][0], it[1]["deadline"]),
    "custom": lambda it: (it[0],),
}
LABELS = {"deadline": "Earliest deadline first", "stakeholder": "Most senior requester first",
          "impact": "Biggest consequence first", "custom": "Your order (as listed)"}


def _schedule(tasks: list, order: list, as_of: str, per_day: float) -> list:
    out, used = [], 0.0
    for idx in order:
        t = tasks[idx]
        used += t["effortHours"] / per_day
        finish = add_workdays(as_of, max(1, math.ceil(used - 1e-9)))
        late = max(0, workdays_between(t["deadline"], finish))
        out.append({"index": idx, "name": t["name"], "finish": finish, "deadline": t["deadline"], "lateDays": late,
                    "requester": t["requester"], "impact": t["impact"]})
    return out


def check(i: dict) -> dict:
    """Rules that span several fields. Returns {field: message}."""
    if i["committedHours"] >= i["hoursPerWeek"]:
        return {"committedHours": "Must be less than your working hours, or there is no time for these tasks"}
    return {}


def compute(i: dict) -> dict:
    tasks = i["tasks"]
    free_week = i["hoursPerWeek"] - i["committedHours"]
    per_day = free_week / 5
    total = sum(t["effortHours"] for t in tasks)
    last_deadline = max(t["deadline"] for t in tasks)
    available = max(0, workdays_between(i["asOf"], last_deadline)) * per_day
    fits = total <= available + 1e-9
    orders = {k: [ix for ix, _ in sorted(enumerate(tasks), key=f)] for k, f in STRATEGIES.items()}

    options = []
    for key, order in orders.items():
        sched = _schedule(tasks, order, i["asOf"], per_day)
        risks, weighted = [], 0
        for s in sched:
            if s["lateDays"] == 0:
                continue
            rw, who = REQUESTER[s["requester"]]
            iw, what = IMPACT[s["impact"]]
            sev = iw + (1 if rw >= 3 else 0) + (1 if s["lateDays"] > 5 else 0)
            weighted += s["lateDays"] * (iw + rw)
            risks.append((sev, f"\"{s['name']}\" finishes {s['finish']}, {s['lateDays']} working day{'s' if s['lateDays'] != 1 else ''} "
                               f"after its {s['deadline']} deadline. That lands on {who}, and {what}."))
        if not fits:
            risks.append((1, f"Not everything fits: the tasks need {rnd(total)} hours, you have about {rnd(available)} free hours "
                             f"before the last deadline. Someone has to hear \"later\". Better now than on the deadline."))
        if not [r for r in risks if r[0] > 0]:
            risks.append((0, "Every task finishes on time with these numbers. Keep a little slack for surprises."))
        same = [k for k, o in orders.items() if o == order and k != key]
        score = sum(s for s, _ in risks)
        options.append({
            "key": key, "label": LABELS[key], "sameAs": same, "order": order, "schedule": sched,
            "lateCount": sum(1 for s in sched if s["lateDays"] > 0), "totalLateDays": sum(s["lateDays"] for s in sched),
            "weightedLateness": weighted, "riskScore": score, "riskLevel": level_of(score),
            "risks": [{"severity": s, "text": t} for s, t in risks],
        })
    # lowest risk = least weighted lateness, then fewest late tasks; first wins on ties (stable)
    best = min(options, key=lambda o: (o["weightedLateness"], o["lateCount"]))
    late_best = best["lateCount"]
    headline = (f"{len(tasks)} tasks, {rnd(total)} hours of work, about {rnd(per_day, 1)} free hours a day. "
                + ("Everything fits before the last deadline if you pick the right order." if fits and late_best == 0 else
                   f"Even the best order leaves {late_best} task{'s' if late_best != 1 else ''} late, so you need to renegotiate something."))
    return {
        "asOf": i["asOf"], "engine": "priorities", "totalHours": rnd(total, 1), "freeHoursPerDay": rnd(per_day, 1),
        "availableHours": rnd(available, 1), "fits": fits, "headline": headline,
        "options": options, "lowestRiskKey": best["key"],
        "assumptions": (f"You have {i['hoursPerWeek']} working hours a week, {i['committedHours']} already taken by meetings and "
                        f"ongoing work, so {rnd(free_week, 1)} free hours a week ({rnd(per_day, 1)} a day). Tasks run one after "
                        f"another on working days from {i['asOf']}. Weekends are skipped. Effort numbers are your estimates."),
    }
