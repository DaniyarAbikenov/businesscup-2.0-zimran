"""Builds the Change Request document and the post-decision debrief. All deterministic."""
from .msg import tr
from .engine.change_request import fmt
from .packs import get_situation

PRIORITY = {"must": "Must-have", "important": "Important", "nice": "Nice-to-have"}


def usd(n) -> str:
    return ("-$" if n < 0 else "$") + fmt(abs(n))


def build_document(inputs, result, option_key, rationale, role, user_email, date, situation_id="client-change-request", sit=None) -> str:
    sit = sit or get_situation(situation_id)
    if sit["engine"] == "priorities":
        return _priorities_document(sit, inputs, result, option_key, rationale, user_email, date)
    if sit["engine"] == "decision":
        return _decision_document(sit, inputs, result, option_key, rationale, user_email, date)
    if sit["engine"] == "estimate":
        return _estimate_document(sit, inputs, result, option_key, rationale, user_email, date)
    opt = next(o for o in result["options"] if o["key"] == option_key)
    a = next(o for o in result["options"] if o["key"] == "accept")
    term = (role or {}).get("terms", {}).get("milestone", "release")
    cap = term.capitalize()
    L = [
        tr('# Change Request: {changeTitle}', changeTitle=inputs['changeTitle']), "",
        tr('Date: {date}', date=date), tr('Prepared by: {user_email}', user_email=user_email), tr('Requested by: {requestedBy}', requestedBy=inputs['requestedBy']),
        tr('Client priority: {priority}', priority=tr(PRIORITY[inputs['priority']])), "",
        tr('## 1. Requested change'), inputs.get("changeDescription") or inputs["changeTitle"], "",
        tr('## 2. Impact if accepted'),
        tr('- Effort: {changeEffortDays} person-days, {totalChangeDays} with {overheadPct}% testing and coordination overhead', changeEffortDays=inputs['changeEffortDays'], totalChangeDays=result['totalChangeDays'], overheadPct=inputs['overheadPct']),
        tr('- Added working time: {addedWorkdays} days (buffer available: {bufferDays} days)', addedWorkdays=a['addedWorkdays'], bufferDays=inputs['bufferDays']),
        tr('- {cap} date: {releaseDate} -> {newReleaseDate}', cap=cap, releaseDate=inputs['releaseDate'], newReleaseDate=a['newReleaseDate'])
        + (tr(' (slips {slipWorkdays} working days)', slipWorkdays=a['slipWorkdays']) if a["slipWorkdays"] else tr(' (unchanged)')),
        tr('- Additional cost: {extraCost}', extraCost=usd(a['extraCost']))
        + (tr(' after {clientCovers} covered by the client', clientCovers=usd(a['costBreakdown']['clientCovers'])) if a["costBreakdown"]["clientCovers"] else ""),
        tr('- Budget remaining afterwards: {budgetAfter}', budgetAfter=usd(a['budgetAfter'])) + (tr(' (OVER BUDGET)') if a["budgetAfter"] < 0 else ""),
        "", tr('## 3. Options considered'),
        tr('| Option | {cap} date | Extra cost now | Risk |', cap=cap), "|---|---|---|---|",
    ]
    for o in result["options"]:
        L.append(f"| {sit['options'][o['key']]['label']} | {o['newReleaseDate']} | {usd(o['extraCost'])} | {o['riskLevel']} |")
    L += ["", tr('## 4. Decision'), f"**{sit['options'][option_key]['label']}.**"]
    if rationale:
        L.append(rationale)
    if option_key == "defer":
        L.append(tr('The change moves to the next {term}. Estimated cost at that point: {laterCost}.', term=term, laterCost=usd(opt['laterCost'])))
    L += ["", tr('## 5. Next steps')]
    L += [f"{n}. {s}" for n, s in enumerate(sit["options"][option_key]["nextSteps"], 1)]
    L += ["", tr('## 6. Approval'), tr('Client approval: ____________________   Date: __________'),
          tr('Project manager: ____________________   Date: __________'), "", tr('Assumptions: {assumptions}', assumptions=result['assumptions'])]
    return "\n".join(L)


def build_debrief(result, option_key, inputs, situation_id="client-change-request", sit=None) -> dict:
    sit = sit or get_situation(situation_id)
    if sit["engine"] == "priorities":
        return _priorities_debrief(sit, result, option_key)
    if sit["engine"] == "decision":
        return _decision_debrief(sit, result, option_key, inputs)
    if sit["engine"] == "estimate":
        return _estimate_debrief(sit, result, option_key, inputs)
    opt = next(o for o in result["options"] if o["key"] == option_key)
    lowest = next(o for o in result["options"] if o["key"] == result["lowestRiskKey"])
    label = lambda k: sit["options"][k]["label"]
    pts = []
    if option_key == result["lowestRiskKey"]:
        pts.append(tr('Your choice, "{option_key}", has the lowest risk score on your numbers. Check that the benefits you are giving up are acceptable.', option_key=label(option_key)))
    else:
        pts.append(tr('On your numbers, "{key}" scored lower risk ({riskLevel}) than your choice ({riskLevel2}). That is fine if you know something the numbers do not. Say what it is in your rationale.', key=label(lowest['key']), riskLevel=lowest['riskLevel'], riskLevel2=opt['riskLevel']))
    pts += [tr('Watch out: {text}', text=r['text']) for r in opt["risks"] if r["severity"] >= 1]
    if option_key == "accept" and opt["slipWorkdays"] == 0:
        pts.append(tr('You absorbed the change within the buffer. Tell the client that the buffer is now used up, so the next change has a visible cost.'))
    if option_key == "accept" and inputs["clientCoversPct"] == 0:
        pts.append(tr('No client funding was entered. If the contract allows it, ask for a funded change order so the cost is visible.'))
    if option_key != "accept":
        pts.append(tr('Offer something concrete alongside your answer: a date, a smaller version or a workaround. A plain "no" or "later" is what clients remember.'))
    return {"points": pts, "pitfalls": sit["pitfalls"], "nextSteps": sit["options"][option_key]["nextSteps"]}



def _forgot(inputs) -> list:
    """What the person said they may be missing: it goes into the document as an assumption, never silently."""
    out = []
    if inputs.get("hiddenHours"):
        out.append(tr("I may be missing about {n} hours a week of other work, and the numbers above already take them off my free time.", n=inputs["hiddenHours"]))
    if inputs.get("forgotten"):
        out.append(tr("Things I may be forgetting: {text}", text=inputs["forgotten"]))
    return ([""] + out) if out else []


# ---------------- Competing priorities ----------------
WHO = {"skip": "my manager's manager", "manager": "you", "client": "the other party", "peer": "a colleague", "self": "me"}


def _status(s) -> str:
    return tr('on time') if s["lateDays"] == 0 else tr('{lateDays} working day{sfx} late', lateDays=s['lateDays'], sfx='s' if s['lateDays'] != 1 else '')


def _priorities_document(sit, inputs, result, option_key, rationale, user_email, date) -> str:
    opt = next(o for o in result["options"] if o["key"] == option_key)
    tasks = inputs["tasks"]
    late = [s for s in opt["schedule"] if s["lateDays"] > 0]
    L = [tr('# Priority proposal: {title}', title=inputs['title']), "", tr('Date: {date}', date=date), tr('From: {user_email}', user_email=user_email), "",
         tr('## Situation'),
         tr('I have {tasks} requests that together need {totalHours} hours. After meetings and ongoing work I have about {freeHoursPerDay} free hours a day.', tasks=len(tasks), totalHours=result['totalHours'], freeHoursPerDay=result['freeHoursPerDay']), ]
    if inputs.get("context"):
        L.append(inputs["context"])
    L += ["", tr('## Proposed order ({lower})', lower=sit['options'][option_key]['label'].lower())]
    for n, s in enumerate(opt["schedule"], 1):
        t = tasks[s["index"]]
        line = tr('{n}. **{name}**: {effortHours} h, done by {finish} (deadline {deadline}, {s}). Requested by {requester}.', n=n, name=s['name'], effortHours=t['effortHours'], finish=s['finish'], deadline=s['deadline'], s=_status(s), requester=tr(WHO[s['requester']]))
        if t.get("note"):
            line += tr(' Note: {note}', note=t['note'])
        L.append(line)
    L += ["", tr('## What moves')]
    if late:
        L += [tr('- {name} would be {lateDays} working day{sfx} late ({finish} instead of {deadline}).', name=s['name'], lateDays=s['lateDays'], sfx='s' if s['lateDays'] != 1 else '', finish=s['finish'], deadline=s['deadline']) for s in late]
        L.append("")
        L.append(tr('**What I need from you:** confirm this order, or tell me which of these can get a new date, a smaller scope or another owner.'))
    else:
        L.append(tr('- Nothing, if my estimates hold. I will flag it the same day if one of them slips.'))
    L += ["", tr('## Orders I compared'), tr('| Order | Late tasks | Late days in total | Risk |'), "|---|---|---|---|"]
    for o in result["options"]:
        L.append(f"| {sit['options'][o['key']]['label']} | {o['lateCount']} | {o['totalLateDays']} | {o['riskLevel']} |")
    L += ["", tr('## Why this order')]
    L.append(rationale or tr('(add your reasoning)'))
    L += _forgot(inputs) + ["", tr('Assumptions: {assumptions}', assumptions=result['assumptions'])]
    return "\n".join(L)


def _priorities_debrief(sit, result, option_key) -> dict:
    opt = next(o for o in result["options"] if o["key"] == option_key)
    best = next(o for o in result["options"] if o["key"] == result["lowestRiskKey"])
    label = lambda k: sit["options"][k]["label"]
    pts = []
    if option_key == best["key"] or opt["weightedLateness"] == best["weightedLateness"]:
        pts.append(tr('Your order, "{option_key}", has the lowest weighted lateness on your numbers.', option_key=label(option_key)))
    else:
        pts.append(tr('On your numbers, "{key}" leaves less damage ({lateCount} late task(s), {totalLateDays} late days) than your choice ({lateCount2} late, {totalLateDays2} days). That is fine if you know something the numbers do not. Say it in your proposal.', key=label(best['key']), lateCount=best['lateCount'], totalLateDays=best['totalLateDays'], lateCount2=opt['lateCount'], totalLateDays2=opt['totalLateDays']))
    pts += [tr('Watch out: {text}', text=r['text']) for r in opt["risks"] if r["severity"] >= 2]
    if not result["fits"]:
        pts.append(tr('No order makes everything fit. The useful move is to ask early which task gets a new date or a smaller scope, not to find the perfect order.'))
    if any(s["requester"] == "skip" and s["lateDays"] > 0 for s in opt["schedule"]):
        pts.append(tr("A request from your manager's manager will be late. Tell your manager first, so they are not surprised."))
    return {"points": pts, "pitfalls": sit["pitfalls"], "nextSteps": sit["options"][option_key]["nextSteps"]}



# ---------------- Estimates and promises ----------------
ASKER = {"manager": "my manager", "client": "the other party", "peer": "a colleague"}


def _estimate_document(sit, inputs, result, option_key, rationale, user_email, date) -> str:
    opt = next(o for o in result["options"] if o["key"] == option_key)
    likely = next(o for o in result["options"] if o["key"] == "likely")
    L = [tr('# Estimate reply: {title}', title=inputs['title']), "", tr('Date: {date}', date=date), tr('From: {user_email}', user_email=user_email), tr('To: {to}', to=tr(ASKER[inputs['requester']])), ""]
    if option_key == "range":
        L += [tr('## Reply'),
              tr('I expect to finish between {dateFrom} and {date}. I will re-check on {recheckDate} and tell you then whether it is closer to {dateFrom} or to {date}.', dateFrom=opt['dateFrom'], date=opt['date'], recheckDate=opt['recheckDate'])]
    else:
        L += [tr('## Reply'), tr('I can have this done by {date}.', date=opt['date']) if option_key != "optimistic"
              else tr('The earliest I can have this done is {date}, if nothing goes wrong. I will tell you as soon as I see it slipping.', date=opt['date'])]
    if inputs.get("askedDeadline"):
        asked = inputs["askedDeadline"]
        if opt["lateDays"]:
            L.append(tr('I know you asked for {asked}. That is {lateDays} working day{sfx} earlier than I can commit to. If {asked} is fixed, tell me what can be cut or who can help, and I will redo the estimate.', asked=asked, lateDays=opt['lateDays'], sfx='s' if opt['lateDays'] != 1 else ''))
        else:
            L.append(tr('That is on or before the {asked} you asked for.', asked=asked))
    L += ["", tr('## What it is based on'),
          tr('- Work: about {meanHours} hours expected (best case {optimisticHours}, most likely {likelyHours}, worst realistic {pessimisticHours}).', meanHours=result['meanHours'], optimisticHours=inputs['optimisticHours'], likelyHours=inputs['likelyHours'], pessimisticHours=inputs['pessimisticHours']),
          tr('- My time: {hoursPerWeek} free hours a week, about {hoursPerDay} real hours a working day after interruptions.', hoursPerWeek=inputs['hoursPerWeek'], hoursPerDay=result['hoursPerDay']),
          tr('- Chance to make {date}: about {probability} %.', date=opt['date'], probability=opt['probability'])]
    if inputs.get("context"):
        L.append(tr('- Context: {context}', context=inputs['context']))
    L += ["", tr('## What could move it'),
          tr('- The work turning out to be at the larger end of my estimate.'),
          tr('- New requests or meetings taking more of my time than planned.'),
          tr('- Waiting for input or reviews from other people.'),
          "", tr('## What I need from you'), tr('Confirm the date, or tell me what to drop or who can help if it needs to be earlier.'),
          "", tr('## The options I compared'), tr('| What I could say | Date | Chance | Risk |'), "|---|---|---|---|"]
    for o in result["options"]:
        d = tr('{frm} to {to}', frm=o['dateFrom'], to=o['date']) if o["key"] == "range" else o["date"]
        L.append(f"| {sit['options'][o['key']]['label']} | {d} | {o['probability']} % | {o['riskLevel']} |")
    L += ["", tr('## Why this one'), rationale or tr('(add your reasoning)')] + _forgot(inputs) + ["", tr('Assumptions: {assumptions}', assumptions=result['assumptions'])]
    return "\n".join(L)


def _estimate_debrief(sit, result, option_key, inputs) -> dict:
    opt = next(o for o in result["options"] if o["key"] == option_key)
    best = next(o for o in result["options"] if o["key"] == result["lowestRiskKey"])
    label = lambda k: sit["options"][k]["label"]
    pts = []
    if option_key == best["key"] or opt["riskScore"] == best["riskScore"]:
        pts.append(tr('Your choice, "{option_key}", has the lowest risk on your numbers.', option_key=label(option_key)))
    else:
        pts.append(tr('On your numbers, "{key}" scored lower risk ({riskLevel}) than your choice ({riskLevel2}). That is fine if you know something the numbers do not. Put it in your reply.', key=label(best['key']), riskLevel=best['riskLevel'], riskLevel2=opt['riskLevel']))
    pts += [tr('Watch out: {text}', text=r['text']) for r in opt["risks"] if r["severity"] >= 1]
    if option_key == "optimistic":
        pts.append(tr('A best-case date turns into a promise the moment you say it. Say clearly that it is the best case.'))
    if option_key == "range":
        pts.append(tr('Put {recheckDate} in your calendar now. A range without the check-in is just a vague answer.', recheckDate=opt['recheckDate']))
    if inputs.get("askedDeadline") and opt["lateDays"]:
        pts.append(tr('Your date is after the one they asked for. Offer a smaller first delivery by their date instead of squeezing the estimate.'))
    return {"points": pts, "pitfalls": sit["pitfalls"], "nextSteps": sit["options"][option_key]["nextSteps"]}



# ---------------- Decision calculator ----------------
def _decision_document(sit, inputs, result, option_key, rationale, user_email, date) -> str:
    opt = next(o for o in result["options"] if o["key"] == option_key)
    crit = result["criteria"]
    L = [tr('# Decision note: {title}', title=inputs['title']), "", tr('Date: {date}', date=date), tr('From: {user_email}', user_email=user_email)]
    if inputs.get("decideBy"):
        L.append(tr('Decision needed by: {decideBy}', decideBy=inputs['decideBy']))
    L += ["", tr('## Decision needed'), inputs["title"]]
    if inputs.get("context"):
        L.append(inputs["context"])
    L += ["", tr('## Recommendation'),
          tr('I recommend **{pick}** ({lower}). It scores {score:g} out of 100 and ranks {rank} of {ranking} on the criteria below.', pick=opt['pick'], lower=sit['options'][option_key]['label'].lower(), score=opt['score'], rank=opt['rank'], ranking=len(result['ranking'])),
          "", tr('## Options compared'), tr('| Option | Score | Rank | ') + " | ".join(f"{c['name']} ({c['weight']})" for c in crit) + " |",
          "|---|---|---|" + "---|" * len(crit)]
    for r in result["ranking"]:
        L.append(f"| {r['name']} | {r['score']:g} | {r['rank']} | " + " | ".join(str(s["score"]) for s in r["scores"]) + " |")
    L += ["", tr('Scores are 1 to 5 (5 is best for me). The number in brackets is the weight of the criterion (5 is critical).'),
          "", tr('## Result'), result["notes"][0], "", tr('Four ways to pick, and what each chooses:')]
    L += [f"- {sit['options'][o['key']]['label']}: {o['pick']}" for o in result["options"]]
    L += ["", tr('## What would change the result'), f"- {result['notes'][1]}", f"- {result['notes'][2]}",
          "", tr('## Risks and how I will handle them')]
    L += [f"- {r['text']}" for r in opt["risks"]]
    L += ["", tr('## What I need from you'), tr('Confirm this, or tell me which score or weight you would change, and I will rerun it.'),
          "", tr('## Why this one'), rationale or tr('(add your reasoning)'), "", tr('Assumptions: {assumptions}', assumptions=result['assumptions'])]
    return "\n".join(L)


def _decision_debrief(sit, result, option_key, inputs) -> dict:
    opt = next(o for o in result["options"] if o["key"] == option_key)
    best = next(o for o in result["options"] if o["key"] == result["lowestRiskKey"])
    label = lambda k: sit["options"][k]["label"]
    pts = []
    if option_key == best["key"] or opt["riskScore"] == best["riskScore"]:
        pts.append(tr('Your strategy, "{option_key}", has the lowest risk on your numbers.', option_key=label(option_key)))
    else:
        pts.append(tr('On your numbers, "{key}" scored lower risk ({riskLevel}) than your choice ({riskLevel2}). That is fine if you know something the numbers do not. Put it in your note.', key=label(best['key']), riskLevel=best['riskLevel'], riskLevel2=opt['riskLevel']))
    pts.append(result["notes"][0])
    pts += [tr('Watch out: {text}', text=r['text']) for r in opt["risks"] if r["severity"] >= 1]
    if not result["agree"]:
        pts.append(tr('The four strategies do not agree. That means the choice depends on what you value most, so say it out loud to the people affected.'))
    if result["robustness"]["label"] != "robust":
        pts.append(tr('The lead is small. A quick check of one score you are unsure about is worth more than a new spreadsheet.'))
    if inputs["reversibility"] == "cannot":
        pts.append(tr('Because this cannot be undone, write down what you will check in two weeks and what would make you wish you had chosen differently.'))
    return {"points": pts, "pitfalls": sit["pitfalls"], "nextSteps": sit["options"][option_key]["nextSteps"]}
