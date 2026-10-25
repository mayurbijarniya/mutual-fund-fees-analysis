"""Run every question against the dbt marts and collect the results."""

from __future__ import annotations

import json

import duckdb

from funds import benchmark, export, fees, paths, survivorship, within_fund
from funds.db import frame, scalar


def coverage(con: duckdb.DuckDBPyConnection) -> dict:
    """The size of what the analysis stands on, quoted in the findings."""
    quarters = frame(
        con,
        "SELECT min(quarter) AS first, max(quarter) AS last, count(DISTINCT quarter) AS n "
        "FROM stg_facts",
    ).row(0, named=True)
    return {
        "first_quarter": quarters["first"],
        "last_quarter": quarters["last"],
        "quarters": quarters["n"],
        "facts": scalar(con, "SELECT count(*) FROM stg_facts"),
        "filings": scalar(con, "SELECT count(*) FROM stg_submissions"),
        "last_filed": scalar(con, "SELECT max(filed_date) FROM stg_submissions").isoformat(),
        "share_classes": scalar(con, "SELECT count(*) FROM dim_share_class"),
        "share_classes_with_fee": scalar(
            con, "SELECT count(*) FROM dim_share_class WHERE median_expense_ratio IS NOT NULL"
        ),
        "funds": scalar(con, "SELECT count(*) FROM dim_fund"),
        "class_years": scalar(con, "SELECT count(*) FROM fct_class_returns"),
        "restated_disagree": scalar(
            con, "SELECT avg((NOT prospectuses_agree)::INT) FROM fct_class_returns"
        ),
        "invalid_expense_ratios": scalar(
            con, "SELECT count(*) FROM int_expense_ratios WHERE NOT is_valid"
        ),
        "expense_ratio_rows": scalar(con, "SELECT count(*) FROM int_expense_ratios"),
        "tickers": scalar(con, "SELECT count(*) FROM dim_share_class WHERE ticker IS NOT NULL"),
    }


def analyze(con: duckdb.DuckDBPyConnection) -> dict:
    fee_years = fees.by_year(con)
    q2, bins = within_fund.analyze(con)
    q3, quintiles = benchmark.analyze(con)
    q4, yearly = survivorship.analyze(con)

    results = {
        "data": coverage(con),
        "fees": {
            "by_year": fee_years.to_dicts(),
            "same_class_change": fees.same_class_change(con),
            "by_status": fees.by_status(con).to_dicts(),
        },
        "within_fund": q2,
        "benchmark": q3,
        "survivorship": q4,
    }
    tables = {
        "fee_trend": fee_years,
        "within_fund_bins": bins,
        "fee_quintiles": quintiles,
        "survivorship": yearly,
        "share_classes": export.share_classes(con),
        "fund_families": export.fund_families(con),
    }
    return {"results": results, "tables": tables}


DECIMALS = 10


def rounded(value):
    """Round every float, so parallel aggregation noise in the 16th digit cannot
    change the file between runs on the same data."""
    if isinstance(value, float):
        return round(value, DECIMALS)
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items()}
    if isinstance(value, list):
        return [rounded(v) for v in value]
    return value


def write(output: dict) -> dict:
    """Write the results and Tableau tables. Returns the results exactly as saved,
    so the findings are rendered from the same rounded numbers the file holds."""
    paths.OUTPUTS.mkdir(parents=True, exist_ok=True)
    text = json.dumps(rounded(output["results"]), indent=2, default=str)
    paths.RESULTS.write_text(text + "\n")
    saved = json.loads(text)
    export.write(output["tables"], saved)
    return saved
