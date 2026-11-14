"""Languages. English is the base. Russian and Kazakh are overlays (app/packs/i18n/<lang>.json) keyed by ids, merged over
the English packs; anything missing falls back to English. The language comes from ?lang=, the X-Lang header, the
signed-in profile, then Accept-Language, then English."""
import copy
import json
from functools import lru_cache
from pathlib import Path

LANGS = ("en", "ru", "kk")
_dir = Path(__file__).parent / "packs" / "i18n"


@lru_cache(maxsize=None)
def overlay(lang: str) -> dict:
    p = _dir / f"{lang}.json"
    return json.loads(p.read_text()) if lang != "en" and p.exists() else {}


def norm(v) -> str | None:
    v = (v or "").strip().lower()[:2]
    return v if v in LANGS else None


def resolve(request=None, profile=None) -> str:
    """The language for this request."""
    if request is not None:
        got = norm(request.query_params.get("lang")) or norm(request.headers.get("x-lang"))
        if got:
            return got
    if profile is not None and norm(getattr(profile, "language", None)):
        return norm(profile.language)
    if request is not None:
        for part in request.headers.get("accept-language", "").split(","):
            got = norm(part.split(";")[0])
            if got:
                return got
    return "en"


def _question(q: dict, ov: dict) -> dict:
    q = dict(q)
    for k in ("label", "help", "why", "placeholder", "itemLabel"):
        if ov.get(k):
            q[k] = ov[k]
    if q.get("defaultRows") and ov.get("defaultRows"):
        q["defaultRows"] = [{**r, "name": ov["defaultRows"].get(r["name"], r["name"])} for r in q["defaultRows"]]
    if q.get("labelFrom") and ov.get("labelTemplate"):
        q["labelFrom"] = {**q["labelFrom"], "template": ov["labelTemplate"]}
    if q.get("options") and ov.get("options"):
        q["options"] = [{**o, "label": ov["options"].get(o["value"], o["label"])} for o in q["options"]]
    if q.get("fields"):
        q["fields"] = [_question(f, (ov.get("fields") or {}).get(f["id"], {})) for f in q["fields"]]
    return q


def _merge_answers(base, ov):
    """Overlay for storyline answers: only text fields. Rows of a list are addressed by their index ("0", "1", ...)."""
    if isinstance(base, list):
        out = list(base)
        for k, v in ov.items():
            i = int(k)
            if i < len(out):
                out[i] = _merge_answers(out[i], v) if isinstance(v, dict) else v
        return out
    out = dict(base)
    for k, v in ov.items():
        out[k] = _merge_answers(base.get(k, {}), v) if isinstance(v, dict) and k in base else v
    return out


def localize_situation(sit: dict, lang: str) -> dict:
    """The situation with the language overlay on top. Custom (AI-made) situations have no overlay and stay as they are."""
    ov = overlay(lang).get("situations", {}).get(sit["id"])
    if not ov:
        return sit
    s = copy.deepcopy(sit)
    for k in ("title", "summary", "category", "documentName"):
        if ov.get(k):
            s[k] = ov[k]
    s["groups"] = [{**g, "title": (ov.get("groups") or {}).get(g["id"], g["title"])} for g in s.get("groups", [])]
    s["questions"] = [_question(q, (ov.get("questions") or {}).get(q["id"], {})) for q in s["questions"]]
    for key, o in s["options"].items():
        oo = (ov.get("options") or {}).get(key, {})
        o["label"] = oo.get("label", o["label"])
        o["nextSteps"] = oo.get("nextSteps") or o["nextSteps"]
    if ov.get("pitfalls"):
        s["pitfalls"] = ov["pitfalls"]
    s["reflectionPrompts"] = [{**p, "label": (ov.get("reflectionPrompts") or {}).get(p["id"], p["label"])} for p in s["reflectionPrompts"]]
    def _story(st):
        o = (ov.get("storylines") or {}).get(st["id"], {})
        out = {**st, **{k: v for k, v in o.items() if k in ("title", "story")}}
        if o.get("answers"):
            out["answers"] = _merge_answers(st["answers"], o["answers"])
        return out
    s["storylines"] = [_story(st) for st in s.get("storylines", [])]
    return s


def localize_roles(pack: dict, lang: str) -> dict:
    ov = overlay(lang)
    if not ov:
        return pack
    out = dict(pack)
    out["roles"] = [{**r, "label": (ov.get("roles") or {}).get(r["id"], r["label"]), "describeExample": (ov.get("describe") or {}).get(r["id"], r.get("describeExample", ""))} for r in pack["roles"]]
    out["fears"] = [{**f, "label": (ov.get("fears") or {}).get(f["id"], f["label"])} for f in pack["fears"]]
    out["tenures"] = [{**t, "label": (ov.get("tenures") or {}).get(t["id"], t["label"])} for t in pack["tenures"]]
    return out


def vocab_situation(sit: dict, role_id: str | None, lang: str) -> dict:
    """Apply the position's words (officer: orders, unit; mayor: council, residents; ...) to the template text of a scenario."""
    from . import msg
    if not role_id or not msg._vocab(role_id, lang):
        return sit
    v = lambda t: msg.vocab(t, role_id, lang) if isinstance(t, str) else t

    def q(x):
        x = dict(x)
        for k in ("label", "help", "why", "placeholder", "itemLabel"):
            if k in x:
                x[k] = v(x[k])
        if x.get("options"):
            x["options"] = [{**o, "label": v(o["label"])} for o in x["options"]]
        if x.get("fields"):
            x["fields"] = [q(f) for f in x["fields"]]
        return x
    s = copy.deepcopy(sit)
    for k in ("title", "summary"):
        s[k] = v(s[k])
    s["groups"] = [{**g, "title": v(g["title"])} for g in s.get("groups", [])]
    s["questions"] = [q(x) for x in s["questions"]]
    for o in s["options"].values():
        o["label"] = v(o["label"])
        o["nextSteps"] = [v(n) for n in o["nextSteps"]]
    s["pitfalls"] = [v(p) for p in s["pitfalls"]]
    s["reflectionPrompts"] = [{**p, "label": v(p["label"])} for p in s["reflectionPrompts"]]
    s["storylines"] = [{**st, "title": v(st["title"]), "story": v(st["story"])} for st in s.get("storylines", [])]
    return s


def pick_storylines(sit: dict, role_id: str | None) -> dict:
    """Examples written for one position show only to that position, and first."""
    out = dict(sit)
    sts = [st for st in sit.get("storylines", []) if not st.get("roles") or role_id in st["roles"]]
    out["storylines"] = sorted(sts, key=lambda st: 0 if st.get("roles") else 1)
    return out
