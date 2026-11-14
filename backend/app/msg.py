"""Server-side texts in the user's language. The English template is the key: tr("Saved {n} files", n=3).
The language of the current request (or of the user being emailed) lives in a context variable, so engines and
document builders do not need it passed around. Tables: app/messages/<lang>.json, English template -> translated
template with the same {placeholders}. A missing entry falls back to the English template."""
import json
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path

lang_var: ContextVar[str] = ContextVar("lang", default="en")
_dir = Path(__file__).parent / "messages"


@lru_cache(maxsize=None)
def table(lang: str) -> dict:
    p = _dir / f"{lang}.json"
    return json.loads(p.read_text()) if lang != "en" and p.exists() else {}


def set_lang(lang: str):
    return lang_var.set(lang)


def current() -> str:
    return lang_var.get()


def tr(template: str, **kw) -> str:
    s = table(lang_var.get()).get(template, template)
    return s.format(**kw) if kw else s


def plural(n: int, one: str, few: str, many: str) -> str:
    """Russian-style plural: forms for 1, 2-4 and 5+ (Kazakh and English use the first and the last)."""
    lang = lang_var.get()
    if lang == "ru":
        m10, m100 = n % 10, n % 100
        return one if m10 == 1 and m100 != 11 else few if 2 <= m10 <= 4 and not 12 <= m100 <= 14 else many
    return one if n == 1 else many
