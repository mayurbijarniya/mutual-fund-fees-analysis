"""Q1: what do funds charge, and how has it changed?

The headline trend mixes two things: funds cutting their prices, and the mix of
funds changing as cheap ones launch and expensive ones close. Following the
same share classes across years separates the two.
"""

from __future__ import annotations

import duckdb
import polars as pl

from funds.db import frame

FIRST_YEAR = 2016
LAST_FULL_YEAR = 2025


def by_year(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    return frame(
        con,
        """
        SELECT prospectus_year                                      AS year,
               count(*)                                             AS share_classes,
               quantile_cont(effective_expense_ratio, 0.25)         AS p25,
               median(effective_expense_ratio)                      AS median,
               quantile_cont(effective_expense_ratio, 0.75)         AS p75,
               avg(effective_expense_ratio)                         AS mean,
               avg(has_fee_waiver::INT)                             AS share_with_waiver
        FROM fct_class_fees
        WHERE prospectus_year >= ?
        GROUP BY 1
        ORDER BY 1
        """,
        [FIRST_YEAR],
    )


def same_class_change(
    con: duckdb.DuckDBPyConnection, start: int = FIRST_YEAR, end: int = LAST_FULL_YEAR
) -> dict:
    """Fee change for classes filing in both years, against the change across all classes."""
    row = frame(
        con,
        """
        WITH a AS (SELECT class_id, effective_expense_ratio AS fee FROM fct_class_fees
                   WHERE prospectus_year = $start),
             b AS (SELECT class_id, effective_expense_ratio AS fee FROM fct_class_fees
                   WHERE prospectus_year = $end)
        SELECT count(*)                         AS classes,
               median(a.fee)                    AS median_start,
               median(b.fee)                    AS median_end,
               median(b.fee - a.fee)            AS median_change,
               avg((b.fee < a.fee)::INT)        AS share_cut,
               avg((b.fee > a.fee)::INT)        AS share_raised
        FROM a JOIN b USING (class_id)
        """,
        {"start": start, "end": end},
    ).row(0, named=True)
    return {"start_year": start, "end_year": end, **row}


def by_status(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    return frame(
        con,
        """
        SELECT status,
               count(*)                         AS share_classes,
               median(median_expense_ratio)     AS median_expense_ratio
        FROM dim_share_class
        WHERE median_expense_ratio IS NOT NULL
        GROUP BY 1
        ORDER BY 1
        """,
    )
