"""DuckDB session helper: run SQL files with path templating."""
from __future__ import annotations

from pathlib import Path

import duckdb

from . import config


def connect(readonly: bool = False) -> duckdb.DuckDBPyConnection:
    config.GOLD_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(config.GOLD_DB))
    con.execute("SET TimeZone='UTC';")
    return con


def run_sql_file(con: duckdb.DuckDBPyConnection, path: Path, raw_dir: Path) -> None:
    """Execute a SQL file, substituting {raw_dir} placeholders."""
    sql = Path(path).read_text(encoding="utf-8")
    sql = sql.replace("{raw_dir}", str(raw_dir).replace("\\", "/"))
    con.execute(sql)


def run_pipeline(con: duckdb.DuckDBPyConnection) -> list[tuple[str, str]]:
    executed: list[tuple[str, str]] = []
    for fname in ["01_staging.sql", "02_clean.sql", "03_golden.sql", "04_forensics.sql"]:
        run_sql_file(con, config.SQL_DIR / fname, config.RAW_DIR)
        executed.append((fname, "ok"))
    return executed


def tables(con: duckdb.DuckDBPyConnection) -> list[str]:
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='main' ORDER BY table_name"
    ).fetchall()
    return [r[0] for r in rows]


def head(con: duckdb.DuckDBPyConnection, table: str, n: int = 5):
    return con.execute(f"SELECT * FROM {table} LIMIT {n}").fetchdf()
