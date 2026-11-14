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
    if q.get("labelFrom") and ov.get("labelTemplate"):
        q["labelFrom"] = {**q["labelFrom"], "template": ov["labelTemplate"]}
    if q.get("options") and ov.get("options"):
        q["options"] = [{**o, "label": ov["options"].get(o["value"], o["label"])} for o in q["options"]]
    if q.get("fields"):
        q["fields"] = [_question(f, (ov.get("fields") or {}).get(f["id"], {})) for f in q["fields"]]
    return q


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
    s["storylines"] = [{**st, **{k: v for k, v in (ov.get("storylines") or {}).get(st["id"], {}).items() if k in ("title", "story")}} for st in s.get("storylines", [])]
    return s


def localize_roles(pack: dict, lang: str) -> dict:
    ov = overlay(lang)
    if not ov:
        return pack
    out = dict(pack)
    out["roles"] = [{**r, "label": (ov.get("roles") or {}).get(r["id"], r["label"])} for r in pack["roles"]]
    out["fears"] = [{**f, "label": (ov.get("fears") or {}).get(f["id"], f["label"])} for f in pack["fears"]]
    out["tenures"] = [{**t, "label": (ov.get("tenures") or {}).get(t["id"], t["label"])} for t in pack["tenures"]]
    return out
