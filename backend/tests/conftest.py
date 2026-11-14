"""Tests run against real Postgres and Redis (compose services, or local ones via env vars)."""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://roleshift:roleshift@localhost:5432/roleshift_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.cache import get_redis
from app.db import engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def migrated():
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
def clean(migrated):
    with engine.begin() as c:
        c.execute(text("TRUNCATE users, profiles, cases, journal RESTART IDENTITY CASCADE"))
    get_redis().flushdb()


@pytest.fixture(autouse=True)
def english_by_default():
    from app import msg
    msg.set_lang("en")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def make_client():
    """Independent clients so cookies do not mix between users."""
    return lambda: TestClient(app)
