"""The product is English only by default: a saved or requested language is ignored unless LANGUAGES enables it."""
from app import i18n


def test_only_english_when_not_enabled(monkeypatch):
    monkeypatch.setattr(i18n, "LANGS", ("en",))
    assert i18n.norm("ru") is None and i18n.norm("kk") is None and i18n.norm("en") == "en"
    req = type("R", (), {"query_params": {"lang": "ru"}, "headers": {"x-lang": "kk", "accept-language": "ru-RU,ru;q=0.9"}})()
    assert i18n.resolve(req, type("P", (), {"language": "ru"})()) == "en"


def test_overlays_still_work_when_enabled(monkeypatch):
    monkeypatch.setattr(i18n, "LANGS", ("en", "ru", "kk"))
    assert i18n.norm("ru") == "ru"


def test_form_steps_cover_every_group_once():
    """The form wizard: every built-in scenario has 3 to 4 named steps and each question group sits in exactly one."""
    from app import packs
    for s in packs.situations:
        groups = [g["id"] for g in s["groups"]]
        in_steps = [g for st in s["steps"] for g in st["groups"]]
        assert sorted(in_steps) == sorted(groups), s["id"]
        assert 3 <= len(s["steps"]) <= 4 and all(st["title"] for st in s["steps"]), s["id"]
