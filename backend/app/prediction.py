"""Predict first, then reveal. Before the numbers appear the person can make a quick guess; the server then scores it against
the engine's result on the same inputs. This measures agreement with the calculator on the person's own numbers, not the quality
of decisions in the real world. The frontend never decides a score."""
from datetime import date, timedelta

from . import packs
from .engine.change_request import workdays_between
from .errors import ApiError
from .msg import fmt_iso, tr

ORDERS = ["deadline", "stakeholder", "impact", "custom"]
ENGINES = ("priorities", "estimate", "decision")
MIN_FOR_TREND = 3


def _int(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def clean(sit: dict, inputs: dict, raw) -> dict | None:
    """Validated guess for this scenario, or None when the person skipped (or the scenario has no guess step)."""
    e = sit["engine"]
    if raw is None or e not in ENGINES:
        return None
    if not isinstance(raw, dict):
        raise ApiError(400, "Check your guess", {"prediction": "Invalid"})
    errs, out = {}, {}
    if e == "priorities":
        n = len(inputs["tasks"])
        late = _int(raw.get("lateCount"))
        if late is None or not 0 <= late <= n:
            errs["prediction.lateCount"] = "Choose a number from the list"
        else:
            out["lateCount"] = late
        if raw.get("bestOrder") not in ORDERS:
            errs["prediction.bestOrder"] = "Choose one of the options"
        else:
            out["bestOrder"] = raw["bestOrder"]
        if raw.get("cheapest") in ("scope", "pay"):  # optional: asked only when money and scope data were entered
            out["cheapest"] = raw["cheapest"]
    elif e == "estimate":
        d = raw.get("date")
        try:
            dd = date.fromisoformat(d) if isinstance(d, str) and len(d) == 10 else None
        except ValueError:
            dd = None
        start = date.fromisoformat(inputs["asOf"])
        if dd is None or not start <= dd <= start + timedelta(days=400):
            errs["prediction.date"] = "Enter a valid date"
        else:
            out["date"] = d
        c = raw.get("confidence")
        if c is not None:
            if _int(c) is None or not 0 <= c <= 100:
                errs["prediction.confidence"] = "Must be between 0 and 100"
            else:
                out["confidence"] = c
    else:
        w = _int(raw.get("winner"))
        if w is None or not 0 <= w < len(inputs["options"]):
            errs["prediction.winner"] = "Choose one of the options"
        else:
            out["winner"] = w
    if errs:
        raise ApiError(400, "Check your guess", errs)
    return out


def score(sit: dict, guess: dict | None, result: dict, inputs: dict) -> dict | None:
    """Numbers only (no sentences): parts with hit/error and an overall 0..1. Texts are made when the case is read."""
    if not guess:
        return None
    e = sit["engine"]
    opts = {o["key"]: o for o in result["options"]}
    if e == "priorities":
        late = opts["custom"]["lateCount"]
        parts = [{"key": "lateCount", "guess": guess["lateCount"], "actual": late, "error": guess["lateCount"] - late, "hit": guess["lateCount"] == late},
                 {"key": "bestOrder", "guess": guess["bestOrder"], "actual": result["lowestRiskKey"], "hit": guess["bestOrder"] == result["lowestRiskKey"]}]
        ls = {l["key"]: l for l in result.get("levers") or []}
        if guess.get("cheapest") and "scope" in ls and "pay" in ls and ls["pay"]["money"]["total"] is not None:
            m = {k: ls[k]["money"]["total"] for k in ("scope", "pay")}
            cheap = min(m, key=m.get) if m["scope"] != m["pay"] else guess["cheapest"]  # a tie counts for either
            parts.append({"key": "cheapest", "guess": guess["cheapest"], "actual": cheap, "hit": guess["cheapest"] == cheap})
        overall = sum(p["hit"] for p in parts) / len(parts)
    elif e == "estimate":
        safe = opts["safe"]["date"]
        err = workdays_between(safe, guess["date"])  # positive: later (more cautious) than the safe date
        parts = [{"key": "safeDate", "guess": guess["date"], "actual": safe, "error": err, "hit": abs(err) <= 1}]
        overall = 1.0 if abs(err) <= 1 else 0.5 if abs(err) <= 3 else 0.0
    else:
        win = result["ranking"][0]["index"]
        parts = [{"key": "winner", "guess": guess["winner"], "actual": win, "hit": guess["winner"] == win}]
        overall = 1.0 if parts[0]["hit"] else 0.0
    return {"parts": parts, "overall": overall}


def reveal(sit: dict, guess: dict | None, sc: dict | None, result: dict, inputs: dict) -> dict | None:
    """Texts in the active language: what was guessed, what the numbers say, one friendly sentence and what was not counted."""
    if not guess or not sc:
        return None
    e = sit["engine"]
    lab = lambda k: sit["options"][k]["label"]
    items = []
    for p in sc["parts"]:
        if p["key"] == "lateCount":
            items.append({"label": tr("Tasks that finish late if you keep your order"), "guess": str(p["guess"]), "actual": str(p["actual"]), "hit": p["hit"]})
        elif p["key"] == "bestOrder":
            items.append({"label": tr("Order with the lowest risk"), "guess": lab(p["guess"]), "actual": lab(p["actual"]), "hit": p["hit"]})
        elif p["key"] == "cheapest":
            name = lambda k: tr("Cut scope on the late tasks") if k == "scope" else tr("Pay for extra hours")
            items.append({"label": tr("Cheaper way to fix lateness in total money"), "guess": name(p["guess"]), "actual": name(p["actual"]), "hit": p["hit"]})
        elif p["key"] == "safeDate":
            gap = tr("{n} working days later", n=p["error"]) if p["error"] > 1 else tr("{n} working days earlier", n=-p["error"]) if p["error"] < -1 else tr("within a day")
            items.append({"label": tr("Date you could safely commit to"), "guess": fmt_iso(p["guess"]), "actual": fmt_iso(p["actual"]), "hit": p["hit"], "gap": gap})
        else:
            names = [o["name"] for o in inputs["options"]]
            items.append({"label": tr("Option that scores highest"), "guess": names[p["guess"]], "actual": names[p["actual"]], "hit": p["hit"]})
    o = sc["overall"]
    if o >= 1:
        sentence = tr("You called it: your intuition and the numbers agree here.")
    elif o >= 0.5:
        sentence = tr("Close. Part of your guess matched the numbers, and the rest is worth a second look.")
    else:
        sentence = tr("The numbers saw something you did not this time. That is exactly what practice is for.")
    missed = None
    if o < 1:
        if e == "priorities":
            risks = [r for r in next(x for x in result["options"] if x["key"] == "custom")["risks"] if r["severity"] > 0]
            missed = max(risks, key=lambda r: r["severity"])["text"] if risks else None
        elif e == "estimate":
            extra = round(result["meanHours"] - inputs["likelyHours"], 1)
            missed = tr("The spread between your best and worst case adds about {n} hours to your most likely estimate, and that is what pushes the safe date out.", n=extra) if extra > 0.5 \
                else tr("Interruptions leave you only about {n} real hours a working day.", n=result["hoursPerDay"])
        else:
            missed = result["notes"][1] if len(result.get("notes", [])) > 1 else None
    return {"items": items, "overall": o, "sentence": sentence, "missed": missed}
