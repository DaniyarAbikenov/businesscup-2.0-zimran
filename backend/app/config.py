import os

from sqlalchemy.engine import URL


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


ON_VERCEL = env("VERCEL") == "1"  # serverless: no background loop, no connection pool, secure cookie, public URL from Vercel


def _first(*names: str) -> str:
    return next((env(n) for n in names if env(n)), "")


def _normalize_pg(url: str) -> str:
    """postgres:// and postgresql:// (Neon, Vercel Postgres) -> the psycopg 3 driver. Query parameters such as sslmode=require stay."""
    for old in ("postgres://", "postgresql://"):
        if url.startswith(old):
            return "postgresql+psycopg://" + url[len(old):]
    return url


def _database_url():
    """DATABASE_URL wins if set (or the Vercel/Neon names POSTGRES_URL, POSTGRES_URL_NON_POOLING). Otherwise the URL is built
    from parts, so passwords with characters like @ / : # work without manual URL-encoding."""
    given = _first("DATABASE_URL", "POSTGRES_URL", "POSTGRES_URL_NON_POOLING")
    if given:
        return _normalize_pg(given)
    return URL.create(
        "postgresql+psycopg",
        username=env("POSTGRES_USER", "roleshift"),
        password=env("POSTGRES_PASSWORD", "roleshift"),
        host=env("POSTGRES_HOST", "localhost"),
        port=int(env("POSTGRES_PORT", "5432")),
        database=env("POSTGRES_DB", "roleshift"),
    )


DATABASE_URL = _database_url()
REDIS_URL = _first("REDIS_URL", "KV_URL", "UPSTASH_REDIS_URL") or "redis://localhost:6379/0"  # rediss:// (TLS) works as is
COOKIE_SECURE = env("COOKIE_SECURE", "true" if ON_VERCEL else "false") == "true"
CRON_SECRET = env("CRON_SECRET")  # Vercel Cron sends it as "Authorization: Bearer <secret>"
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
LLM_MODEL = env("LLM_MODEL", "claude-opus-5-5")
DEMO_MODE = env("DEMO_MODE", "true") == "true"
DEMO_PER_HOUR = int(env("DEMO_PER_HOUR", "10"))  # demo accounts one address may create per hour
DEMO_KEEP_DAYS = int(env("DEMO_KEEP_DAYS", "7"))  # the daily job removes demo accounts older than this
SESSION_DAYS = 14

# Pricing. Free users can start FREE_CASES situations of their own; the pass unlocks everything for PASS_DAYS.
FREE_CASES = int(env("FREE_CASES", "3"))
PASS_PRICE_CENTS = int(env("PASS_PRICE_CENTS", "1900"))
PASS_DAYS = int(env("PASS_DAYS", "90"))
# Built-in test checkout: no payment provider, no card data, the purchase is stored as provider "test".
TEST_CHECKOUT = env("TEST_CHECKOUT", "true") == "true"

# Email (optional). With SMTP_HOST empty the app uses a "log mailer": each email is written to the server log and kept
# in the Redis list "outbox" (last 50), nothing is sent. APP_URL is the public address used in email links.
SMTP_HOST = env("SMTP_HOST")
SMTP_PORT = int(env("SMTP_PORT", "587"))
SMTP_USER = env("SMTP_USER")
SMTP_PASSWORD = env("SMTP_PASSWORD")
SMTP_FROM = env("SMTP_FROM", "RoleShift <no-reply@localhost>")
APP_URL = (env("APP_URL") or (f"https://{env('VERCEL_PROJECT_PRODUCTION_URL')}" if env("VERCEL_PROJECT_PRODUCTION_URL") else "http://localhost:5173")).rstrip("/")
