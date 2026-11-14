"""Server-side texts in the user's language. The English template is the key: tr("Saved {n} files", n=3).
The language of the current request (or of the user being emailed) lives in a context variable, so engines and
document builders do not need it passed around. Tables: app/messages/<lang>.json, English template -> translated
template with the same {placeholders}. A missing entry falls back to the English template."""
import json
import re
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path

lang_var: ContextVar[str] = ContextVar("lang", default="en")
role_var: ContextVar[str | None] = ContextVar("role", default=None)
_dir = Path(__file__).parent / "messages"


@lru_cache(maxsize=None)
def table(lang: str) -> dict:
    p = _dir / f"{lang}.json"
    return json.loads(p.read_text()) if lang != "en" and p.exists() else {}


def set_lang(lang: str):
    return lang_var.set(lang)


def current() -> str:
    return lang_var.get()


def set_role(role_id):
    return role_var.set(role_id)


_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt_iso(iso: str, lang: str | None = None) -> str:
    y, m, d = iso.split("-")
    return f"{d}.{m}.{y}" if (lang or lang_var.get()) in ("ru", "kk") else f"{_MONTHS[int(m) - 1]} {int(d)}, {y}"


def localize_dates(text, lang: str | None = None):
    """ISO dates inside sentences become 14.11.2026 (ru, kk) or Nov 14, 2026 (en). A string that is just a date is data and stays."""
    if not isinstance(text, str) or _ISO.fullmatch(text.strip()):
        return text
    return _ISO.sub(lambda m: fmt_iso(m.group(0), lang), text)


def localize_dates_deep(x, lang: str | None = None):
    if isinstance(x, str):
        return localize_dates(x, lang)
    if isinstance(x, list):
        return [localize_dates_deep(i, lang) for i in x]
    if isinstance(x, dict):
        return {k: localize_dates_deep(v, lang) for k, v in x.items()}
    return x


@lru_cache(maxsize=None)
def _vocab(role_id, lang):
    if not role_id:
        return None
    p = Path(__file__).parent / "packs" / "roles.json"
    role = next((r for r in json.loads(p.read_text(encoding="utf-8"))["roles"] if r["id"] == role_id), None)
    pairs = ((role or {}).get("vocab") or {}).get(lang)
    if not pairs:
        return None
    mapping = {a.lower(): b for a, b in pairs}
    rx = re.compile(r"(?<![\w])(" + "|".join(re.escape(a) for a in sorted(mapping, key=len, reverse=True)) + r")(?![\w])", re.IGNORECASE)
    return rx, mapping


def vocab(text, role_id=None, lang: str | None = None):
    """The words of the person's position: the template text of a scenario or a document, never what the user typed."""
    if not isinstance(text, str):
        return text
    v = _vocab(role_id if role_id is not None else role_var.get(), lang or lang_var.get())
    if not v:
        return text
    rx, mapping = v

    def rep(m):
        r = mapping[m.group(1).lower()]
        return r[0].upper() + r[1:] if m.group(1)[0].isupper() else r
    return rx.sub(rep, text)


def tr(template: str, **kw) -> str:
    s = vocab(table(lang_var.get()).get(template, template))
    return s.format(**kw) if kw else s


def plural(n: int, one: str, few: str, many: str) -> str:
    """Russian-style plural: forms for 1, 2-4 and 5+ (Kazakh and English use the first and the last)."""
    lang = lang_var.get()
    if lang == "ru":
        m10, m100 = n % 10, n % 100
        return one if m10 == 1 and m100 != 11 else few if 2 <= m10 <= 4 and not 12 <= m100 <= 14 else many
    return one if n == 1 else many
