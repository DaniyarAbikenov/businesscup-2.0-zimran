import os

from sqlalchemy.engine import URL


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _database_url():
    """DATABASE_URL wins if set. Otherwise the URL is built from parts, so passwords with
    characters like @ / : # work without manual URL-encoding."""
    if env("DATABASE_URL"):
        return env("DATABASE_URL")
    return URL.create(
        "postgresql+psycopg",
        username=env("POSTGRES_USER", "roleshift"),
        password=env("POSTGRES_PASSWORD", "roleshift"),
        host=env("POSTGRES_HOST", "localhost"),
        port=int(env("POSTGRES_PORT", "5432")),
        database=env("POSTGRES_DB", "roleshift"),
    )


DATABASE_URL = _database_url()
REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")
COOKIE_SECURE = env("COOKIE_SECURE", "false") == "true"
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
LLM_MODEL = env("LLM_MODEL", "claude-opus-5-5")
DEMO_MODE = env("DEMO_MODE", "true") == "true"
SESSION_DAYS = 14

# Pricing. Free users can start FREE_CASES situations of their own; the pass unlocks everything for PASS_DAYS.
FREE_CASES = int(env("FREE_CASES", "3"))
PASS_PRICE_CENTS = int(env("PASS_PRICE_CENTS", "2900"))
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
APP_URL = env("APP_URL", "http://localhost:5173").rstrip("/")
