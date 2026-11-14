from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from . import config

if config.ON_VERCEL:  # serverless: every invocation may be a new process, so no pool; no prepared statements (works behind a pooler like Neon's)
    engine = create_engine(config.DATABASE_URL, poolclass=NullPool, connect_args={"prepare_threshold": None, "connect_timeout": 10})
else:
    engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
