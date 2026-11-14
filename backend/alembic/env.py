from alembic import context
from sqlalchemy import create_engine

from app import config, models  # noqa: F401  (models import registers tables)
from app.db import Base

if context.config.config_file_name:
    from logging.config import fileConfig

    fileConfig(context.config.config_file_name)

target_metadata = Base.metadata


def run_migrations_online():
    engine = create_engine(config.DATABASE_URL)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
