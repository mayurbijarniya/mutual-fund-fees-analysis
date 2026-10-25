"""Q4: how much does survivorship flatter the averages?

A dataset built from today's funds only contains the ones that survived.
Funds that closed or merged were, on average, the weaker ones, so averages over
survivors alone overstate what investors actually earned. Each year's average
return is computed twice: over every share class that reported it, and over
only the classes still filing at the end of the data.
"""

from __future__ import annotations

import duckdb
import polars as pl

from funds.db import frame

COHORT_LAST_QUARTER = "2016q4"
FIRST_YEAR = 2016
LAST_YEAR = 2024


def cohort(con: duckdb.DuckDBPyConnection) -> dict:
    """What happened to the share classes that were filing in 2016."""
    row = frame(
        con,
        """
        SELECT count(*)                                         AS share_classes,
               count(*) FILTER (WHERE status = 'stopped filing') AS stopped,
               median(median_expense_ratio) FILTER (WHERE status = 'active')         AS fee_active,
               median(median_expense_ratio) FILTER (WHERE status = 'stopped filing') AS fee_stopped
        FROM dim_share_class
        WHERE first_quarter <= ?
        """,
        [COHORT_LAST_QUARTER],
    ).row(0, named=True)
    row["share_stopped"] = row["stopped"] / row["share_classes"]
    return row


def yearly_bias(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    return frame(
        con,
        """
        SELECT return_year                                              AS year,
               count(*)                                                 AS classes_all,
               count(*) FILTER (WHERE status = 'active')                AS classes_surviving,
               avg(annual_return)                                       AS mean_all,
               avg(annual_return) FILTER (WHERE status = 'active')      AS mean_surviving,
               avg(annual_return) FILTER (WHERE status = 'stopped filing') AS mean_stopped
        FROM fct_class_returns
        WHERE return_year BETWEEN ? AND ?
        GROUP BY 1
        ORDER BY 1
        """,
        [FIRST_YEAR, LAST_YEAR],
    ).with_columns((pl.col("mean_surviving") - pl.col("mean_all")).alias("bias"))


def benchmark_by_status(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    return frame(
        con,
        """
        SELECT horizon_years,
               status,
               count(*)                                 AS share_classes,
               avg((excess_return > 0)::INT)            AS share_beating,
               median(excess_return)                    AS median_excess
        FROM fct_benchmark_excess
        GROUP BY 1, 2
        ORDER BY 1, 2
        """,
    )


def analyze(con: duckdb.DuckDBPyConnection) -> tuple[dict, pl.DataFrame]:
    yearly = yearly_bias(con)
    results = {
        "cohort_2016": cohort(con),
        "mean_yearly_bias": float(yearly["bias"].mean()),
        "years": [FIRST_YEAR, LAST_YEAR],
        "yearly": yearly.to_dicts(),
        "benchmark_by_status": benchmark_by_status(con).to_dicts(),
    }
    return results, yearly
