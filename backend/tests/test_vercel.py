"""Serverless support: connection string names, the daily cron endpoint and its secret."""
import importlib

from app import config


def test_database_urls_are_normalized(monkeypatch):
    for k in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_URL_NON_POOLING"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("POSTGRES_URL", "postgres://u:p@h.neon.tech/db?sslmode=require")
    assert config._database_url() == "postgresql+psycopg://u:p@h.neon.tech/db?sslmode=require"
    monkeypatch.setenv("DATABASE_URL", "postgresql://a:b@x/y")
    assert config._database_url() == "postgresql+psycopg://a:b@x/y"  # DATABASE_URL wins
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://a:b@x/y")
    assert config._database_url() == "postgresql+psycopg://a:b@x/y"


def test_redis_and_app_url_names(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("KV_URL", "rediss://default:t@x.upstash.io:6379")
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_PROJECT_PRODUCTION_URL", "app.vercel.app")
    monkeypatch.delenv("APP_URL", raising=False)
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    try:
        c = importlib.reload(config)
        assert c.REDIS_URL.startswith("rediss://") and c.APP_URL == "https://app.vercel.app" and c.COOKIE_SECURE is True and c.ON_VERCEL
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_cron_needs_the_secret(client, monkeypatch):
    monkeypatch.setattr(config, "CRON_SECRET", "")
    assert client.get("/api/internal/cron/followups").status_code == 404  # off when no secret is set
    monkeypatch.setattr(config, "CRON_SECRET", "s3cret")
    assert client.get("/api/internal/cron/followups").status_code == 404
    assert client.get("/api/internal/cron/followups", headers={"Authorization": "Bearer wrong"}).status_code == 404
    ok = client.get("/api/internal/cron/followups", headers={"Authorization": "Bearer s3cret"})
    assert ok.status_code == 200 and ok.json()["ok"] is True and set(ok.json()) == {"ok", "followups", "day7"}
