"""Builds the Change Request document and the post-decision debrief. All deterministic."""
from .engine.change_request import fmt
from .packs import get_situation

PRIORITY = {"must": "Must-have", "important": "Important", "nice": "Nice-to-have"}


def usd(n) -> str:
    return ("-$" if n < 0 else "$") + fmt(abs(n))


def build_document(inputs, result, option_key, rationale, role, user_email, date) -> str:
    sit = get_situation("client-change-request")
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


def build_debrief(result, option_key, inputs) -> dict:
    sit = get_situation("client-change-request")
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
