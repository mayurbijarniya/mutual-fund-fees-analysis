"""Open the DuckDB warehouse that dbt builds, and run queries against it."""

from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl

from funds import paths


def connect(db: Path = paths.DB) -> duckdb.DuckDBPyConnection:
    if not db.exists():
        raise FileNotFoundError(f"{db} not found; run `funds build` first")
    return duckdb.connect(str(db), read_only=True)


def frame(con: duckdb.DuckDBPyConnection, query: str, params=None) -> pl.DataFrame:
    return con.sql(query, params=params).pl()


def scalar(con: duckdb.DuckDBPyConnection, query: str, params=None):
    """First column of the first row. Fetches everything, so the connection is free after."""
    return con.execute(query, params).fetchall()[0][0]
