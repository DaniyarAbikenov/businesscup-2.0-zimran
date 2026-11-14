"""Mail sending: Resend when a key is set, SMTP from parts or from SMTP_URL, a log mailer otherwise."""
import importlib

from app import config, mailer
from app.cache import get_redis


def test_smtp_url_is_split_into_parts(monkeypatch):
    monkeypatch.setenv("SMTP_URL", "smtps://me%40x.com:p%40ss@smtp.example.com")
    for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    try:
        c = importlib.reload(config)
        assert (c.SMTP_HOST, c.SMTP_PORT, c.SMTP_USER, c.SMTP_PASSWORD) == ("smtp.example.com", 465, "me@x.com", "p@ss")
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_log_mailer_without_keys_and_resend_with_a_key(monkeypatch):
    r = get_redis()
    monkeypatch.setattr(config, "RESEND_API_KEY", "")
    monkeypatch.setattr(config, "SMTP_HOST", "")
    assert mailer.is_log_mailer()
    mailer.send(r, "a@b.c", "Hi", "Body")
    assert r.llen("outbox") == 1  # nothing sent, only kept for reading

    sent = {}

    class Resp:
        def raise_for_status(self):
            pass

    import httpx
    monkeypatch.setattr(httpx, "post", lambda url, **kw: sent.update(url=url, **kw) or Resp())
    monkeypatch.setattr(config, "RESEND_API_KEY", "re_test")
    assert not mailer.is_log_mailer()
    mailer.send(r, "a@b.c", "Hi", "Body")
    assert sent["url"] == "https://api.resend.com/emails" and sent["headers"]["Authorization"] == "Bearer re_test"
    assert sent["json"]["to"] == ["a@b.c"] and sent["json"]["subject"] == "Hi"
    assert r.llen("outbox") == 1  # not logged again
