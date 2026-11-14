import os


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


DATABASE_URL = env("DATABASE_URL", "postgresql+psycopg://roleshift:roleshift@localhost:5432/roleshift")
REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")
COOKIE_SECURE = env("COOKIE_SECURE", "false") == "true"
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
LLM_MODEL = env("LLM_MODEL", "claude-haiku-5-5")
SESSION_DAYS = 14
