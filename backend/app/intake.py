""""Describe your situation in your own words": turns free text into a situation plus pre-filled answers.

Two ways to read the text:
- keywords (always available, no AI): scores each situation by keywords and carries the text over into the
  title and background fields. Numbers stay for the user to enter.
- ai (only when ANTHROPIC_API_KEY is set and the user agreed to send the text): the model proposes the
  situation and the values the person stated.

Either way every value goes through the same validation as the form (validate_answers), one field at a time.
Anything invalid is dropped and listed as "to check", so the AI can never put a value into a case that the
form itself would refuse. Numbers are still computed only by the engines."""
import re

from . import packs
from .validate import validate_answers

KEYWORDS = {
    "competing-priorities": [
        "priorit", "deadline", "too many", "overload", "overtime", "at the same time", "conflicting", "competing",
        "my manager", "boss", "asked me", "tasks", "workload", "no time", "urgent", "this week", "by friday",
        "which first", "juggl", "swamped", "behind",
    ],
    "client-change-request": [
        "client", "customer", "change request", "scope", "requirement", "new feature", "release", "launch date",
        "budget", "contract", "stakeholder wants", "add a feature", "late change", "sprint", "invoice", "penalty",
    ],
}
MAX_NOTES = 5


def catalog() -> list[dict]:
    """A compact description of every situation and its fields, for the AI prompt."""
    out = []
    for s in packs.situations:
        fields = []
        for q in s["questions"]:
            f = {"id": q["id"], "label": q.get("label", q["id"]), "type": q["type"]}
            if q.get("options"):
                f["values"] = [o["value"] for o in q["options"]]
            if q["type"] == "list":
                f["rowFields"] = [{"id": x["id"], "label": x.get("label", x["id"]), "type": x["type"],
                                   **({"values": [o["value"] for o in x["options"]]} if x.get("options") else {})}
                                  for x in q["fields"]]
            fields.append(f)
        out.append({"id": s["id"], "title": s["title"], "summary": s.get("summary", ""), "fields": fields})
    return out


def rule_match(text: str) -> list[tuple[str, int]]:
    """Situations ranked by keyword hits, best first. Ties keep catalog order."""
    t = text.lower()
    scores = [(s["id"], sum(1 for k in KEYWORDS.get(s["id"], []) if k in t)) for s in packs.situations]
    return sorted(scores, key=lambda x: -x[1])


def _first_sentence(text: str, limit: int) -> str:
    s = re.split(r"(?<=[.!?])\s|\n", text.strip(), maxsplit=1)[0].strip()
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def _clean_number(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v
    s = str(v).strip()
    m = re.fullmatch(r"[$€£]?\s*(-?[\d,]*\.?\d+)\s*(k|K)?\s*(%|hours?|hrs?|h|days?|usd|dollars)?", s)
    if not m:
        return s  # let the validator reject it
    n = float(m.group(1).replace(",", ""))
    return n * 1000 if m.group(2) else n


def _one(q: dict, v):
    """Validates a single proposed value against its question. Returns (ok, value)."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return False, None
    if q["type"] == "number":
        v = _clean_number(v)
    vals, errs = validate_answers([{**q, "required": True}], {q["id"]: v})
    return (not errs), vals.get(q["id"])


def sanitize(sit: dict, proposed: dict, rows: list | None = None) -> tuple[dict, list[str], list[str]]:
    """Keeps only values that pass validation. Returns (answers, filled ids, rejected labels)."""
    answers, filled, rejected = {}, [], []
    for q in sit["questions"]:
        if q["type"] == "list":
            kept = []
            for raw in (rows or [])[: q.get("maxRows", 10)]:
                if not isinstance(raw, dict):
                    continue
                row = {}
                for f in q["fields"]:
                    ok, val = _one(f, raw.get(f["id"]))
                    if ok:
                        row[f["id"]] = val
                    elif raw.get(f["id"]) not in (None, ""):
                        rejected.append(f"{q.get('itemLabel', 'Row')}: {f.get('label', f['id'])}")
                if row.get("name"):
                    kept.append(row)
            if kept:
                answers[q["id"]] = kept
                filled.append(q["id"])
            continue
        if q["id"] not in proposed:
            continue
        ok, val = _one(q, proposed[q["id"]])
        if ok:
            answers[q["id"]] = val
            filled.append(q["id"])
        elif proposed[q["id"]] not in (None, ""):
            rejected.append(q.get("label", q["id"]))
    return answers, filled, rejected


def carry_text(sit: dict, text: str, answers: dict, filled: list):
    """Puts the user's own words into the title and background fields if they are still empty."""
    title_id = sit.get("titleField")
    tq = next((q for q in sit["questions"] if q["id"] == title_id), None)
    if tq and title_id not in answers:
        answers[title_id] = _first_sentence(text, tq.get("max", 120))
        filled.append(title_id)
    area = next((q for q in sit["questions"] if q["type"] == "textarea"), None)
    if area and area["id"] not in answers:
        limit = area.get("max", 1000)
        answers[area["id"]] = text.strip() if len(text.strip()) <= limit else text.strip()[: limit - 1].rstrip() + "…"
        filled.append(area["id"])


def result(sit: dict, answers: dict, filled: list, notes: list, source: str, ranked: list) -> dict:
    missing = [q.get("label", q["id"]) for q in sit["questions"]
               if q["id"] not in filled and (q.get("required") or q["type"] == "list") and "default" not in q
               and "defaultDaysFromNow" not in q]
    return {"situationId": sit["id"], "answers": answers, "filled": filled, "missing": missing,
            "notes": notes[:MAX_NOTES], "source": source,
            "alternatives": [sid for sid, _ in ranked if sid != sit["id"]]}


def from_keywords(text: str, note: str | None = None) -> dict:
    ranked = rule_match(text)
    best, score = ranked[0]
    sit = packs.get_situation(best)
    answers, filled = {}, []
    carry_text(sit, text, answers, filled)
    notes = [note] if note else []
    if score == 0:
        notes.append("We could not tell which situation this is. Check that this one fits, or pick another.")
    notes.append("Your text was copied into the form. Enter the numbers yourself.")
    return result(sit, answers, filled, notes, "keywords", ranked)


def from_ai(text: str, proposal: dict) -> dict:
    sid = proposal.get("situationId")
    sit = packs.get_situation(sid) if isinstance(sid, str) else None
    if not sit:
        return from_keywords(text, "The AI could not place this situation, so we matched it by keywords.")
    fields = {f.get("id"): f.get("value") for f in proposal.get("fields") or [] if isinstance(f, dict)}
    answers, filled, rejected = sanitize(sit, fields, proposal.get("tasks") if isinstance(proposal.get("tasks"), list) else [])
    carry_text(sit, text, answers, filled)
    notes = [str(u)[:200] for u in (proposal.get("unclear") or []) if isinstance(u, str) and u.strip()]
    if rejected:
        notes.insert(0, "Some values could not be used and were left empty: " + ", ".join(dict.fromkeys(rejected)) + ".")
    ranked = [(sid, 0)] + [(s["id"], 0) for s in packs.situations if s["id"] != sid]
    return result(sit, answers, filled, notes, "ai", ranked)
