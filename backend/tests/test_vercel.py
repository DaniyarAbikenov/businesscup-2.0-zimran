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
    assert ok.status_code == 200 and ok.json()["ok"] is True and set(ok.json()) == {"ok", "followups", "day7", "demoRemoved"}


def test_demo_accounts_are_limited_per_address_and_old_ones_are_cleaned(client, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app import demo
    from app.db import SessionLocal
    from app.models import User
    monkeypatch.setattr(config, "DEMO_PER_HOUR", 2)
    assert client.post("/api/auth/demo", json={}).status_code == 201
    assert client.post("/api/auth/demo", json={}).status_code == 201
    assert client.post("/api/auth/demo", json={}).status_code == 429  # the third one in the hour
    with SessionLocal() as db:
        old = db.scalars(select(User).order_by(User.id)).first()
        old.created_at = datetime.now(timezone.utc) - timedelta(days=8)
        db.commit()
        assert demo.cleanup(db, 7) == 1  # only the one older than 7 days
        assert len(db.scalars(select(User)).all()) == 1


def test_client_address_comes_from_the_proxy_only_on_vercel(monkeypatch):
    from app.security import client_ip
    req = type("R", (), {"headers": {"x-forwarded-for": "203.0.113.5, 10.0.0.1"}, "client": type("C", (), {"host": "10.0.0.1"})()})()
    monkeypatch.setattr(config, "ON_VERCEL", False)
    assert client_ip(req) == "10.0.0.1"
    monkeypatch.setattr(config, "ON_VERCEL", True)
    assert client_ip(req) == "203.0.113.5"


def test_api_health_touches_nothing(client, monkeypatch):
    from app import main
    monkeypatch.setattr(main, "SessionLocal", lambda: (_ for _ in ()).throw(AssertionError("must not use the database")))
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json() == {"ok": True}
