from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

engine_kwargs: dict = {"pool_pre_ping": True}
if settings.is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in settings.resolved_database_url:
        engine_kwargs["poolclass"] = StaticPool
else:
    engine_kwargs["connect_args"] = {"connect_timeout": 10}

engine = create_engine(settings.resolved_database_url, **engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema() -> None:
    """Create tables and add columns that create_all will not alter in place."""
    from app import models  # noqa: F401 — register metadata

    Base.metadata.create_all(bind=engine)
    _add_column_if_missing("books", "media_type", "VARCHAR(20) DEFAULT 'book'")
    _ensure_active_loan_index()


def _add_column_if_missing(table: str, column: str, ddl: str) -> None:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns(table)}
    if column in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


ACTIVE_LOAN_INDEX = "uq_loans_active_item"


def _ensure_active_loan_index() -> None:
    """One active loan per item. create_all will not add this to an existing table."""
    inspector = inspect(engine)
    if "loans" not in inspector.get_table_names():
        return
    existing = {idx["name"] for idx in inspector.get_indexes("loans")}
    if ACTIVE_LOAN_INDEX in existing:
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                f"CREATE UNIQUE INDEX {ACTIVE_LOAN_INDEX} "
                "ON loans (item_kind, item_id) WHERE returned_at IS NULL"
            )
        )
