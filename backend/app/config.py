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
LLM_MODEL = env("LLM_MODEL", "claude-haiku-5-5")
DEMO_MODE = env("DEMO_MODE", "true") == "true"
SESSION_DAYS = 14
