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
