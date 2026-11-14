"""Builds the Change Request document and the post-decision debrief. All deterministic."""
from .engine.change_request import fmt
from .packs import get_situation

PRIORITY = {"must": "Must-have", "important": "Important", "nice": "Nice-to-have"}


def usd(n) -> str:
    return ("-$" if n < 0 else "$") + fmt(abs(n))


def build_document(inputs, result, option_key, rationale, role, user_email, date, situation_id="client-change-request", sit=None) -> str:
    sit = sit or get_situation(situation_id)
    if sit["engine"] == "priorities":
        return _priorities_document(sit, inputs, result, option_key, rationale, user_email, date)
    if sit["engine"] == "estimate":
        return _estimate_document(sit, inputs, result, option_key, rationale, user_email, date)
    opt = next(o for o in result["options"] if o["key"] == option_key)
    a = next(o for o in result["options"] if o["key"] == "accept")
    term = (role or {}).get("terms", {}).get("milestone", "release")
    cap = term.capitalize()
    L = [
        f"# Change Request: {inputs['changeTitle']}", "",
        f"Date: {date}", f"Prepared by: {user_email}", f"Requested by: {inputs['requestedBy']}",
        f"Client priority: {PRIORITY[inputs['priority']]}", "",
        "## 1. Requested change", inputs.get("changeDescription") or inputs["changeTitle"], "",
        "## 2. Impact if accepted",
        f"- Effort: {inputs['changeEffortDays']} person-days, {result['totalChangeDays']} with {inputs['overheadPct']}% testing and coordination overhead",
        f"- Added working time: {a['addedWorkdays']} days (buffer available: {inputs['bufferDays']} days)",
        f"- {cap} date: {inputs['releaseDate']} -> {a['newReleaseDate']}"
        + (f" (slips {a['slipWorkdays']} working days)" if a["slipWorkdays"] else " (unchanged)"),
        f"- Additional cost: {usd(a['extraCost'])}"
        + (f" after {usd(a['costBreakdown']['clientCovers'])} covered by the client" if a["costBreakdown"]["clientCovers"] else ""),
        f"- Budget remaining afterwards: {usd(a['budgetAfter'])}" + (" (OVER BUDGET)" if a["budgetAfter"] < 0 else ""),
        "", "## 3. Options considered",
        f"| Option | {cap} date | Extra cost now | Risk |", "|---|---|---|---|",
    ]
    for o in result["options"]:
        L.append(f"| {sit['options'][o['key']]['label']} | {o['newReleaseDate']} | {usd(o['extraCost'])} | {o['riskLevel']} |")
    L += ["", "## 4. Decision", f"**{sit['options'][option_key]['label']}.**"]
    if rationale:
        L.append(rationale)
    if option_key == "defer":
        L.append(f"The change moves to the next {term}. Estimated cost at that point: {usd(opt['laterCost'])}.")
    L += ["", "## 5. Next steps"]
    L += [f"{n}. {s}" for n, s in enumerate(sit["options"][option_key]["nextSteps"], 1)]
    L += ["", "## 6. Approval", "Client approval: ____________________   Date: __________",
          "Project manager: ____________________   Date: __________", "", f"Assumptions: {result['assumptions']}"]
    return "\n".join(L)


def build_debrief(result, option_key, inputs, situation_id="client-change-request", sit=None) -> dict:
    sit = sit or get_situation(situation_id)
    if sit["engine"] == "priorities":
        return _priorities_debrief(sit, result, option_key)
    if sit["engine"] == "estimate":
        return _estimate_debrief(sit, result, option_key, inputs)
    opt = next(o for o in result["options"] if o["key"] == option_key)
    lowest = next(o for o in result["options"] if o["key"] == result["lowestRiskKey"])
    label = lambda k: sit["options"][k]["label"]
    pts = []
    if option_key == result["lowestRiskKey"]:
        pts.append(f"Your choice, \"{label(option_key)}\", has the lowest risk score on your numbers. Check that the benefits you are giving up are acceptable.")
    else:
        pts.append(f"On your numbers, \"{label(lowest['key'])}\" scored lower risk ({lowest['riskLevel']}) than your choice ({opt['riskLevel']}). That is fine if you know something the numbers do not. Say what it is in your rationale.")
    pts += [f"Watch out: {r['text']}" for r in opt["risks"] if r["severity"] >= 1]
    if option_key == "accept" and opt["slipWorkdays"] == 0:
        pts.append("You absorbed the change within the buffer. Tell the client that the buffer is now used up, so the next change has a visible cost.")
    if option_key == "accept" and inputs["clientCoversPct"] == 0:
        pts.append("No client funding was entered. If the contract allows it, ask for a funded change order so the cost is visible.")
    if option_key != "accept":
        pts.append("Offer something concrete alongside your answer: a date, a smaller version or a workaround. A plain \"no\" or \"later\" is what clients remember.")
    return {"points": pts, "pitfalls": sit["pitfalls"], "nextSteps": sit["options"][option_key]["nextSteps"]}



# ---------------- Competing priorities ----------------
WHO = {"skip": "my manager's manager", "manager": "you", "client": "the client", "peer": "a colleague", "self": "me"}


def _status(s) -> str:
    return "on time" if s["lateDays"] == 0 else f"{s['lateDays']} working day{'s' if s['lateDays'] != 1 else ''} late"


def _priorities_document(sit, inputs, result, option_key, rationale, user_email, date) -> str:
    opt = next(o for o in result["options"] if o["key"] == option_key)
    tasks = inputs["tasks"]
    late = [s for s in opt["schedule"] if s["lateDays"] > 0]
    L = [f"# Priority proposal: {inputs['title']}", "", f"Date: {date}", f"From: {user_email}", "",
         "## Situation",
         f"I have {len(tasks)} requests that together need {result['totalHours']} hours. After meetings and ongoing work "
         f"I have about {result['freeHoursPerDay']} free hours a day.", ]
    if inputs.get("context"):
        L.append(inputs["context"])
    L += ["", f"## Proposed order ({sit['options'][option_key]['label'].lower()})"]
    for n, s in enumerate(opt["schedule"], 1):
        t = tasks[s["index"]]
        line = f"{n}. **{s['name']}**: {t['effortHours']} h, done by {s['finish']} (deadline {s['deadline']}, {_status(s)}). Requested by {WHO[s['requester']]}."
        if t.get("note"):
            line += f" Note: {t['note']}"
        L.append(line)
    L += ["", "## What moves"]
    if late:
        L += [f"- {s['name']} would be {s['lateDays']} working day{'s' if s['lateDays'] != 1 else ''} late ({s['finish']} instead of {s['deadline']})." for s in late]
        L.append("")
        L.append("**What I need from you:** confirm this order, or tell me which of these can get a new date, a smaller scope or another owner.")
    else:
        L.append("- Nothing, if my estimates hold. I will flag it the same day if one of them slips.")
    L += ["", "## Orders I compared", "| Order | Late tasks | Late days in total | Risk |", "|---|---|---|---|"]
    for o in result["options"]:
        L.append(f"| {sit['options'][o['key']]['label']} | {o['lateCount']} | {o['totalLateDays']} | {o['riskLevel']} |")
    L += ["", "## Why this order"]
    L.append(rationale or "(add your reasoning)")
    L += ["", f"Assumptions: {result['assumptions']}"]
    return "\n".join(L)


def _priorities_debrief(sit, result, option_key) -> dict:
    opt = next(o for o in result["options"] if o["key"] == option_key)
    best = next(o for o in result["options"] if o["key"] == result["lowestRiskKey"])
    label = lambda k: sit["options"][k]["label"]
    pts = []
    if option_key == best["key"] or opt["weightedLateness"] == best["weightedLateness"]:
        pts.append(f"Your order, \"{label(option_key)}\", has the lowest weighted lateness on your numbers.")
    else:
        pts.append(f"On your numbers, \"{label(best['key'])}\" leaves less damage ({best['lateCount']} late task(s), {best['totalLateDays']} late days) "
                   f"than your choice ({opt['lateCount']} late, {opt['totalLateDays']} days). That is fine if you know something the numbers do not. Say it in your proposal.")
    pts += [f"Watch out: {r['text']}" for r in opt["risks"] if r["severity"] >= 2]
    if not result["fits"]:
        pts.append("No order makes everything fit. The useful move is to ask early which task gets a new date or a smaller scope, not to find the perfect order.")
    if any(s["requester"] == "skip" and s["lateDays"] > 0 for s in opt["schedule"]):
        pts.append("A request from your manager's manager will be late. Tell your manager first, so they are not surprised.")
    return {"points": pts, "pitfalls": sit["pitfalls"], "nextSteps": sit["options"][option_key]["nextSteps"]}



# ---------------- Estimates and promises ----------------
ASKER = {"manager": "my manager", "client": "the client", "peer": "a colleague"}


def _estimate_document(sit, inputs, result, option_key, rationale, user_email, date) -> str:
    opt = next(o for o in result["options"] if o["key"] == option_key)
    likely = next(o for o in result["options"] if o["key"] == "likely")
    L = [f"# Estimate reply: {inputs['title']}", "", f"Date: {date}", f"From: {user_email}", f"To: {ASKER[inputs['requester']]}", ""]
    if option_key == "range":
        L += ["## Reply",
              f"I expect to finish between {opt['dateFrom']} and {opt['date']}. I will re-check on {opt['recheckDate']} and tell you then "
              f"whether it is closer to {opt['dateFrom']} or to {opt['date']}."]
    else:
        L += ["## Reply", f"I can have this done by {opt['date']}." if option_key != "optimistic"
              else f"The earliest I can have this done is {opt['date']}, if nothing goes wrong. I will tell you as soon as I see it slipping."]
    if inputs.get("askedDeadline"):
        asked = inputs["askedDeadline"]
        if opt["lateDays"]:
            L.append(f"I know you asked for {asked}. That is {opt['lateDays']} working day{'s' if opt['lateDays'] != 1 else ''} earlier than I can commit to. "
                     f"If {asked} is fixed, tell me what can be cut or who can help, and I will redo the estimate.")
        else:
            L.append(f"That is on or before the {asked} you asked for.")
    L += ["", "## What it is based on",
          f"- Work: about {result['meanHours']} hours expected (best case {inputs['optimisticHours']}, most likely {inputs['likelyHours']}, worst realistic {inputs['pessimisticHours']}).",
          f"- My time: {inputs['hoursPerWeek']} free hours a week, about {result['hoursPerDay']} real hours a working day after interruptions.",
          f"- Chance to make {opt['date']}: about {opt['probability']} %."]
    if inputs.get("context"):
        L.append(f"- Context: {inputs['context']}")
    L += ["", "## What could move it",
          "- The work turning out to be at the larger end of my estimate.",
          "- New requests or meetings taking more of my time than planned.",
          "- Waiting for input or reviews from other people.",
          "", "## What I need from you", "Confirm the date, or tell me what to drop or who can help if it needs to be earlier.",
          "", "## The options I compared", "| What I could say | Date | Chance | Risk |", "|---|---|---|---|"]
    for o in result["options"]:
        d = f"{o['dateFrom']} to {o['date']}" if o["key"] == "range" else o["date"]
        L.append(f"| {sit['options'][o['key']]['label']} | {d} | {o['probability']} % | {o['riskLevel']} |")
    L += ["", "## Why this one", rationale or "(add your reasoning)", "", f"Assumptions: {result['assumptions']}"]
    return "\n".join(L)


def _estimate_debrief(sit, result, option_key, inputs) -> dict:
    opt = next(o for o in result["options"] if o["key"] == option_key)
    best = next(o for o in result["options"] if o["key"] == result["lowestRiskKey"])
    label = lambda k: sit["options"][k]["label"]
    pts = []
    if option_key == best["key"] or opt["riskScore"] == best["riskScore"]:
        pts.append(f"Your choice, \"{label(option_key)}\", has the lowest risk on your numbers.")
    else:
        pts.append(f"On your numbers, \"{label(best['key'])}\" scored lower risk ({best['riskLevel']}) than your choice ({opt['riskLevel']}). "
                   "That is fine if you know something the numbers do not. Put it in your reply.")
    pts += [f"Watch out: {r['text']}" for r in opt["risks"] if r["severity"] >= 1]
    if option_key == "optimistic":
        pts.append("A best-case date turns into a promise the moment you say it. Say clearly that it is the best case.")
    if option_key == "range":
        pts.append(f"Put {opt['recheckDate']} in your calendar now. A range without the check-in is just a vague answer.")
    if inputs.get("askedDeadline") and opt["lateDays"]:
        pts.append("Your date is after the one they asked for. Offer a smaller first delivery by their date instead of squeezing the estimate.")
    return {"points": pts, "pitfalls": sit["pitfalls"], "nextSteps": sit["options"][option_key]["nextSteps"]}
