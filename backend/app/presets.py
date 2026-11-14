"""Situations a person makes from their own description ("AI creates a new situation").

The AI never writes code or numbers. It fills a PRESET on an engine that already exists (change_request or
priorities): the engine fixes the question set and the option keys, the AI may only
- reword question labels and help texts,
- rename the options and write their next steps,
- write pitfalls and reflection prompts,
- propose one example storyline.
Everything the AI proposes is validated here, one field at a time, with the same rules as the forms. Anything
unknown or invalid is dropped; overlong text is cut. The result is a full situation dict (template + overrides)
that works like a built-in one. All numbers still come from the engine."""
import copy
import hashlib
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import intake, packs
from .errors import ApiError
from .models import CustomSituation

TEMPLATES = {"change_request": "client-change-request", "priorities": "competing-priorities"}
ENGINE_HELP = {
    "change_request": "Someone asks for extra work late in a project. The person decides: accept it, defer it or decline it. "
                      "The engine calculates effort, new date, cost and risk from team size, rate, budget, buffer and effort.",
    "priorities": "Two to five tasks from different people compete for the person's limited free hours. The engine compares four "
                  "orders of work (earliest deadline, most senior requester, biggest consequence, the person's own) and shows what ends up late.",
}
CAPS = {"title": 120, "summary": 400, "label": 120, "help": 300, "option": 80, "step": 300, "pitfall": 300, "prompt": 200,
        "storyTitle": 80, "story": 500}
MAX_STEPS, MAX_PITFALLS, MAX_PER_USER = 6, 8, 20
PLUS_DAYS = re.compile(r"^\+(\d{1,3})$")
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _text(v, cap: int) -> str:
    if not isinstance(v, str):
        return ""
    v = re.sub(r"[ \t]+", " ", _CTRL.sub("", v)).strip()
    return v if len(v) <= cap else v[: cap - 1].rstrip() + "…"


def template(engine: str) -> dict:
    return packs.get_situation(TEMPLATES[engine])


def engine_specs() -> list[dict]:
    """What the AI may fill in, per engine: the fixed question ids and option keys."""
    out = []
    for engine, tid in TEMPLATES.items():
        t = packs.get_situation(tid)
        qs = []
        for q in t["questions"]:
            item = {"id": q["id"], "label": q.get("label", q["id"]), "type": q["type"]}
            if q.get("options"):
                item["values"] = [o["value"] for o in q["options"]]
            if q["type"] == "list":
                item["rowFields"] = [{"id": f["id"], "label": f.get("label", f["id"]), "type": f["type"],
                                      **({"values": [o["value"] for o in f["options"]]} if f.get("options") else {})} for f in q["fields"]]
            qs.append(item)
        out.append({"engine": engine, "whatItDoes": ENGINE_HELP[engine], "questions": qs,
                    "options": {k: o["label"] for k, o in t["options"].items()},
                    "reflectionPromptIds": [p["id"] for p in t["reflectionPrompts"]]})
    return out


def _all_question_ids(t: dict) -> set:
    ids = set()
    for q in t["questions"]:
        ids.add(q["id"])
        ids.update(f["id"] for f in q.get("fields", []))
    return ids


def _story(t: dict, raw) -> tuple[dict, dict]:
    """Validates the proposed storyline. Returns (normalized for storage, answers with daysFromNow markers)."""
    if not isinstance(raw, dict):
        return {}, {}
    title, story = _text(raw.get("title"), CAPS["storyTitle"]), _text(raw.get("story"), CAPS["story"])
    qs = {q["id"]: q for q in t["questions"]}
    fields, keep, answers = {}, [], {}
    for f in raw.get("fields") if isinstance(raw.get("fields"), list) else []:
        if isinstance(f, dict) and f.get("id") in qs and qs[f["id"]]["type"] != "list" and f["id"] not in fields:
            fields[f["id"]] = f.get("value")
    for fid, val in fields.items():
        q, marker = qs[fid], None
        if q["type"] == "date" and isinstance(val, str) and PLUS_DAYS.match(val.strip()):
            marker = int(PLUS_DAYS.match(val.strip()).group(1))
            val = packs.add_days(packs.today(), marker)
        ok, clean = intake._one(q, val)
        if ok:
            answers[fid] = {"daysFromNow": marker} if marker is not None else clean
            keep.append({"id": fid, "value": f"+{marker}" if marker is not None else str(clean)})
    rows, keep_rows = [], []
    lq = next((q for q in t["questions"] if q["type"] == "list"), None)
    for raw_row in (raw.get("tasks") if isinstance(raw.get("tasks"), list) else [])[: lq.get("maxRows", 5) if lq else 0]:
        if not isinstance(raw_row, dict):
            continue
        row, marker = dict(raw_row), None
        d = row.get("deadline")
        if isinstance(d, str) and PLUS_DAYS.match(d.strip()):
            marker = int(PLUS_DAYS.match(d.strip()).group(1))
            row["deadline"] = packs.add_days(packs.today(), marker)
        kept = intake.sanitize(t, {}, [row])[0].get(lq["id"])
        required = [f["id"] for f in lq["fields"] if f.get("required")]
        if kept and all(k in kept[0] for k in required):  # an example row must be complete, not half-filled
            clean = kept[0]
            rows.append({**clean, **({"deadline": {"daysFromNow": marker}} if marker is not None and "deadline" in clean else {})})
            keep_rows.append({k: (f"+{marker}" if k == "deadline" and marker is not None else str(v)) for k, v in clean.items()})
    if lq and rows:
        answers[lq["id"]] = rows
    if not (title and story and (keep or keep_rows)):
        return {}, {}
    return {"title": title, "story": story, "fields": keep, "tasks": keep_rows}, answers


def normalize(raw) -> dict:
    """Keeps only what is valid. Raises 422 when the preset has no usable engine, title or summary.
    The result is idempotent: normalize(normalize(x)) == normalize(x)."""
    if not isinstance(raw, dict):
        raise ApiError(422, "The AI answer could not be used")
    engine = raw.get("engine")
    if engine not in TEMPLATES:
        raise ApiError(422, "The AI picked a kind of situation we do not support yet")
    t = template(engine)
    title, summary = _text(raw.get("title"), CAPS["title"]), _text(raw.get("summary"), CAPS["summary"])
    if not title or not summary:
        raise ApiError(422, "The AI did not produce a title and a summary")
    ids, labels = _all_question_ids(t), {}
    for item in raw.get("labels") if isinstance(raw.get("labels"), list) else []:
        if isinstance(item, dict) and item.get("id") in ids and item["id"] not in labels:
            lab, hlp = _text(item.get("label"), CAPS["label"]), _text(item.get("help"), CAPS["help"])
            if lab or hlp:
                labels[item["id"]] = {"id": item["id"], "label": lab, "help": hlp}
    options = {}
    for item in raw.get("options") if isinstance(raw.get("options"), list) else []:
        if isinstance(item, dict) and item.get("key") in t["options"] and item["key"] not in options:
            steps = [s for s in (_text(x, CAPS["step"]) for x in (item.get("nextSteps") if isinstance(item.get("nextSteps"), list) else [])) if s][:MAX_STEPS]
            options[item["key"]] = {"key": item["key"], "label": _text(item.get("label"), CAPS["option"]), "nextSteps": steps}
    pitfalls = [p for p in (_text(x, CAPS["pitfall"]) for x in (raw.get("pitfalls") if isinstance(raw.get("pitfalls"), list) else [])) if p][:MAX_PITFALLS]
    pids = [p["id"] for p in t["reflectionPrompts"]]
    prompts = {}
    for item in raw.get("reflectionPrompts") if isinstance(raw.get("reflectionPrompts"), list) else []:
        if isinstance(item, dict) and item.get("id") in pids and item["id"] not in prompts and _text(item.get("label"), CAPS["prompt"]):
            prompts[item["id"]] = {"id": item["id"], "label": _text(item["label"], CAPS["prompt"])}
    story, _ = _story(t, raw.get("storyline"))
    return {"engine": engine, "title": title, "summary": summary, "labels": list(labels.values()), "options": list(options.values()),
            "pitfalls": pitfalls, "reflectionPrompts": list(prompts.values()), **({"storyline": story} if story else {})}


def build(preset: dict, slug: str = "draft") -> dict:
    """The full situation: the engine's template with the preset's words on top."""
    p = normalize(preset)
    t = copy.deepcopy(template(p["engine"]))
    for item in p["labels"]:
        for q in t["questions"]:
            for node in [q, *q.get("fields", [])]:
                if node["id"] == item["id"]:
                    if item["label"]:
                        node["label"] = item["label"]
                    if item["help"]:
                        node["help"] = item["help"]
    for item in p["options"]:
        o = t["options"][item["key"]]
        if item["label"]:
            o["label"] = item["label"]
        if item["nextSteps"]:
            o["nextSteps"] = item["nextSteps"]
    if p["pitfalls"]:
        t["pitfalls"] = p["pitfalls"]
    for item in p["reflectionPrompts"]:
        next(x for x in t["reflectionPrompts"] if x["id"] == item["id"])["label"] = item["label"]
    story, answers = _story(t, p.get("storyline"))
    t["storylines"] = [{"id": "ai", "title": story["title"], "story": story["story"], "answers": answers}] if story else []
    t.update(id="my-" + slug, title=p["title"], summary=p["summary"], category="My situations", aiMade=True)
    return t


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:30].strip("-")
    return s or "situation-" + hashlib.sha1(title.encode()).hexdigest()[:6]


def unique_slug(db: Session, user_id: int, title: str) -> str:
    base, n = slugify(title), 1
    taken = set(db.scalars(select(CustomSituation.slug).where(CustomSituation.user_id == user_id)))
    slug = base
    while slug in taken:
        n += 1
        slug = f"{base[:36]}-{n}"
    return slug


def count(db: Session, user_id: int) -> int:
    return db.scalar(select(func.count()).select_from(CustomSituation).where(CustomSituation.user_id == user_id)) or 0


def for_user(db: Session, user_id: int) -> list[dict]:
    rows = db.scalars(select(CustomSituation).where(CustomSituation.user_id == user_id).order_by(CustomSituation.id)).all()
    return [build(r.preset, r.slug) for r in rows]


def resolve(db: Session, user_id: int, sid) -> dict | None:
    """A built-in situation, or one of this user's own. Another user's id never resolves."""
    s = packs.get_situation(sid)
    if s or not isinstance(sid, str) or not sid.startswith("my-"):
        return s
    row = db.scalar(select(CustomSituation).where(CustomSituation.user_id == user_id, CustomSituation.slug == sid[3:]))
    return build(row.preset, row.slug) if row else None
