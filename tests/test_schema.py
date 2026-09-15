from sqlalchemy import inspect, text

from app.db import ACTIVE_LOAN_INDEX, _add_column_if_missing, engine, ensure_schema


def test_ensure_schema_is_idempotent_and_adds_columns():
    ensure_schema()
    ensure_schema()
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS schema_probe (id INTEGER PRIMARY KEY)"))
    _add_column_if_missing("schema_probe", "extra", "VARCHAR(20) DEFAULT 'x'")
    _add_column_if_missing("schema_probe", "extra", "VARCHAR(20) DEFAULT 'x'")
    columns = {col["name"] for col in inspect(engine).get_columns("schema_probe")}
    assert "extra" in columns
    books = {col["name"] for col in inspect(engine).get_columns("books")}
    assert "media_type" in books
    tables = set(inspect(engine).get_table_names())
    assert "borrowers" in tables
    assert "loans" in tables
    loan_indexes = {idx["name"] for idx in inspect(engine).get_indexes("loans")}
    assert ACTIVE_LOAN_INDEX in loan_indexes
