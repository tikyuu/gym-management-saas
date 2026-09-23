from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import Session

from app.settings import DatabaseSettings


@lru_cache
def get_engine() -> Engine:
    settings = DatabaseSettings()
    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=settings.db_username,
        password=settings.db_password.get_secret_value(),
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
    )
    return create_engine(
        database_url,
        connect_args={
            "sslmode": "verify-full",
            "sslrootcert": settings.db_ssl_root_cert,
        },
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
    )


def get_db_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
