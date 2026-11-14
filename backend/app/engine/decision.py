"""Deterministic decision calculator: a weighted score for every option, how robust the winner is, and four
strategies for picking. No randomness, no LLM: the same inputs always give the same numbers.

Formulas:
  weighted score of an option = sum(weight * score) / (sum(weight) * 5) * 100        (0 to 100; score 5 is best)
  margin = score of the winner - score of the runner-up, in points of 0-100
  robustness: margin >= 10 robust, 4 to 10 close call, under 4 too close to call
  what would change the winner: the smallest single change that makes the runner-up strictly better than the winner
    - one score: the winner's score on one criterion goes down, or the runner-up's goes up, by 1 or 2 points
      (kept inside 1-5; the criterion with the smaller weight comes first)
    - one weight: one criterion's weight moves by 1 (inside 1-5) and the winner changes
Strategies (the options you compare):
  best     highest weighted score
  safest   highest worst-criterion score (ties: weighted score)
  equal    highest score if all criteria weigh the same
  heaviest     highest score if only the two heaviest criteria count (ties: listed order)
Risk of a strategy's pick: how far its weighted score is below the best (under 5 points: 1, under 10: 2, else 3),
+2 if it scores 1-2 on a criterion you weighted 4-5 (+1 if the weight is lower), plus one shared amount for the
decision itself: min(3, impact * uncertainty // 2) where impact = how hard to undo (easy 0, costly 1, cannot 2)
+ 1 if other teams or a client are affected, and uncertainty = how close the winner is (robust 0, close 1, too
close 2) + how unsure you are of your scores (high 0, medium 1, low 2)."""
from .change_request import level_of, rnd

REV = {"easy": 0, "costly": 1, "cannot": 2}
REV_TEXT = {"easy": "easy to undo", "costly": "costly to undo", "cannot": "impossible to undo"}
CONF = {"high": 0, "medium": 1, "low": 2}
WHO = {"me": ("only you", 0), "team": ("your team", 0), "other_teams": ("other teams", 1), "client": ("a client", 1)}
STRATEGIES = ["best", "safest", "equal", "heaviest"]
MAX_CRITERIA = 6


def check(i: dict) -> dict:
    """Every option needs a score of 1-5 for every criterion row. Returns {field: message}."""
    errs, n = {}, len(i["criteria"])
    for r, o in enumerate(i["options"]):
        for k in range(n):
            if not 1 <= (o.get(f"s{k + 1}") or 0) <= 5:
                errs[f"options.{r}.s{k + 1}"] = "Score from 1 to 5"
    return errs


def _total(weights: list, scores: list) -> int:
    return sum(w * s for w, s in zip(weights, scores))


def _argmax(keys: list) -> int:
    """Index of the largest key; the first one wins ties."""
    best = 0
    for n, k in enumerate(keys):
        if k > keys[best]:
            best = n
    return best


def _flip(names, weights, scores, win: int, run: int, crit: list):
    cand = []
    for d in (1, 2):
        for k, w in enumerate(weights):
            base_w, base_r = scores[win][k], scores[run][k]
            if base_w - d >= 1 and _total(weights, scores[win]) - w * d < _total(weights, scores[run]):
                cand.append((d, w, k, 0, {"side": "winner", "criterion": crit[k], "from": base_w, "to": base_w - d}))
            if base_r + d <= 5 and _total(weights, scores[win]) < _total(weights, scores[run]) + w * d:
                cand.append((d, w, k, 1, {"side": "runnerUp", "criterion": crit[k], "from": base_r, "to": base_r + d}))
    if not cand:
        return None
    best = min(cand, key=lambda c: c[:4])
    return {**best[4], "points": best[0], "option": names[win] if best[4]["side"] == "winner" else names[run]}


def compute(i: dict) -> dict:
    crit = [c["name"] for c in i["criteria"]]
    weights = [c["weight"] for c in i["criteria"]]
    names = [o["name"] for o in i["options"]]
    n = len(crit)
    scores = [[o[f"s{k + 1}"] for k in range(n)] for o in i["options"]]
    W = sum(weights)
    pct = [_total(weights, s) / (W * 5) * 100 for s in scores]
    order = sorted(range(len(names)), key=lambda x: (-pct[x], x))  # stable on ties
    rank = {o: r + 1 for r, o in enumerate(order)}
    win, run = order[0], order[1]
    margin = pct[win] - pct[run]
    label = "robust" if margin >= 10 else "close call" if margin >= 4 else "too close to call"

    flip_score = _flip(names, weights, scores, win, run, crit)
    flip_weight = None
    for k in range(n):
        for delta in (-1, 1):
            if not 1 <= weights[k] + delta <= 5:
                continue
            w2 = weights[:k] + [weights[k] + delta] + weights[k + 1:]
            new = _argmax([_total(w2, s) for s in scores])
            if new != win:
                flip_weight = {"criterion": crit[k], "from": weights[k], "to": weights[k] + delta, "newWinner": names[new]}
                break
        if flip_weight:
            break
    if label == "robust":
        robust_text = f"\"{names[win]}\" leads \"{names[run]}\" by {rnd(margin, 1):g} points: the result is robust."
    else:
        robust_text = f"\"{names[win]}\" leads \"{names[run]}\" by only {rnd(margin, 1):g} points: {label}."
    notes = [robust_text]
    notes.append(
        f"Smallest score change that flips it: {'lower' if flip_score['side'] == 'winner' else 'raise'} \"{flip_score['option']}\" on "
        f"\"{flip_score['criterion']}\" from {flip_score['from']} to {flip_score['to']}." if flip_score else
        "No single score change of up to 2 points flips the winner.")
    notes.append(
        f"Smallest weight change that flips it: \"{flip_weight['criterion']}\" from {flip_weight['from']} to {flip_weight['to']} makes \"{flip_weight['newWinner']}\" the winner."
        if flip_weight else "Moving any one weight by 1 does not change the winner.")

    # strategies
    picks = {
        "best": win,
        "safest": _argmax([(min(s), pct[o]) for o, s in enumerate(scores)]),
        "equal": _argmax([sum(s) for s in scores]),
        "heaviest": _argmax([sum(weights[k] * s[k] for k in sorted(range(n), key=lambda k: (-weights[k], k))[:2]) for s in scores]),
    }
    impact = REV[i["reversibility"]] + WHO[i["whoAffected"]][1]
    uncertainty = (0 if label == "robust" else 1 if label == "close call" else 2) + CONF[i["confidence"]]
    shared = min(3, impact * uncertainty // 2)
    options = []
    for key in STRATEGIES:
        p = picks[key]
        gap = pct[win] - pct[p]
        risks = []
        if gap > 1e-9:
            risks.append((1 if gap < 5 else 2 if gap < 10 else 3,
                          f"\"{names[p]}\" scores {rnd(pct[p], 1):g} against {rnd(pct[win], 1):g} for \"{names[win]}\", {rnd(gap, 1):g} points lower on your own weights."))
        weak = [(weights[k], k) for k in range(n) if scores[p][k] <= 2]
        if weak:
            w, k = max(weak)
            risks.append((2 if w >= 4 else 1, f"\"{names[p]}\" scores {scores[p][k]} on \"{crit[k]}\", which you weighted {w} of 5."))
        if shared:
            who = WHO[i["whoAffected"]][0]
            advice = "try a cheap test or a trial first, or ask someone who knows the area to check your scores" if (REV[i["reversibility"]] == 2 or CONF[i["confidence"]] == 2) \
                else "ask for a second opinion on the scores before you commit"
            risks.append((shared, f"This decision is {REV_TEXT[i['reversibility']]}, it affects {who}, you are {i['confidence']}-confident in your scores and the result is {label}. Before committing, {advice}."))
        if not risks:
            risks.append((0, f"No warning signs on your numbers: \"{names[p]}\" scores {rnd(pct[p], 1):g} and the result is {label}."))
        score = sum(s for s, _ in risks)
        options.append({"key": key, "pick": names[p], "pickIndex": p, "score": rnd(pct[p], 1), "rank": rank[p],
                        "sameAs": [k for k in STRATEGIES if k != key and picks[k] == p],
                        "riskScore": score, "riskLevel": level_of(score), "risks": [{"severity": s, "text": t} for s, t in risks]})
    agree = len(set(picks.values())) == 1
    ranking = [{"index": o, "name": names[o], "score": rnd(pct[o], 1), "rank": rank[o], "marginToNext": rnd(pct[o] - pct[order[r + 1]], 1) if r + 1 < len(order) else None,
                "worst": min(scores[o]), "scores": [{"criterion": crit[k], "weight": weights[k], "score": scores[o][k]} for k in range(n)]} for r, o in enumerate(order)]
    best_risk = min(options, key=lambda x: x["riskScore"])  # stable: list order wins ties
    headline = (f"\"{names[win]}\" scores {rnd(pct[win], 1):g} out of 100, \"{names[run]}\" {rnd(pct[run], 1):g}: {label}. "
                + ("All four strategies pick the same option." if agree else
                   "The strategies disagree: " + "; ".join(f"{LABELS[k].lower()}: {names[picks[k]]}" for k in STRATEGIES) + "."))
    return {
        "engine": "decision", "asOf": i["asOf"], "headline": headline, "ranking": ranking, "robustness": {"label": label, "margin": rnd(margin, 1)},
        "notes": notes, "flipScore": flip_score, "flipWeight": flip_weight, "agree": agree, "criteria": [{"name": c, "weight": w} for c, w in zip(crit, weights)],
        "options": options, "lowestRiskKey": best_risk["key"], "winner": names[win],
        "assumptions": (f"Weighted score = sum(weight x score) / (sum of weights x 5) x 100, with your weights {', '.join(f'{c} {w}' for c, w in zip(crit, weights))} and your scores (1-5, 5 is best). "
                        f"Robust means the lead is 10 points or more, a close call 4 to 10, too close to call under 4. Four strategies: best weighted score, safest (best worst-criterion score), "
                        f"best with equal weights, best counting only the two heaviest criteria. Risk adds the gap to the best option, weak spots on heavy criteria, and how hard the decision is to undo "
                        f"given who is affected and how sure you are of your scores. The scores are your own judgement: the calculator only shows what follows from them."),
    }


LABELS = {"best": "Best weighted score", "safest": "Safest option", "equal": "Best with equal weights", "heaviest": "Best on the two heaviest criteria"}
