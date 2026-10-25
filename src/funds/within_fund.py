"""Q2: do fees come straight out of returns?

Share classes of one fund hold the same portfolio and differ only in what they
charge, so they are close to a controlled experiment. Within each fund and
year, each class's return is compared with the fund's average return that year,
and its fee with the fund's average fee. If fees come straight out of returns,
a class charging one percentage point more returns one point less: a slope of
-1. Standard errors are clustered by fund, because a fund's classes move
together year after year.

The fee matched to a year's return matters. A class's typical fee across all
years is a noisy measure of what it charged in a given year, and noise in the
fee pulls the slope toward zero. The main specification uses the fee reported
in the prospectus filed the following year, which states that year's actual
expenses. The other two are reported as robustness checks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import duckdb
import polars as pl
import statsmodels.api as sm

from funds.db import frame

BIN_WIDTH = 0.001  # 0.1 percentage point of fee difference
MAX_FEE_GAP = 0.02
MIN_BIN_OBSERVATIONS = 50

# Fee matched to each year's return: name -> SQL for the fee column and its join.
FEE_JOIN = "JOIN fct_class_fees f ON f.class_id = r.class_id AND f.prospectus_year = r.return_year"
SPECIFICATIONS = {
    "next_prospectus": ("f.effective_expense_ratio", FEE_JOIN + " + 1"),
    "same_year_prospectus": ("f.effective_expense_ratio", FEE_JOIN),
    "typical_fee": ("r.median_expense_ratio", ""),
}
MAIN = "next_prospectus"


@dataclass(frozen=True)
class Slope:
    slope: float
    low: float
    high: float
    p_value: float
    observations: int
    funds: int
    fund_years: int


def deviations(con: duckdb.DuckDBPyConnection, specification: str = MAIN) -> pl.DataFrame:
    """Each class's return and fee relative to its fund's average in that year.

    Rows come back sorted and the averages are taken in polars, so the floating
    point sums run in the same order every time; DuckDB's parallel window
    aggregates do not, and the last digits of the slope would drift between runs.
    """
    fee, join = SPECIFICATIONS[specification]
    rows = frame(
        con,
        f"""
        SELECT r.series_id, r.return_year, r.class_id, r.annual_return, {fee} AS fee
        FROM fct_class_returns r
        {join}
        WHERE {fee} IS NOT NULL
        ORDER BY r.series_id, r.return_year, r.class_id
        """,
    )
    group = ["series_id", "return_year"]
    return (
        rows.filter(pl.len().over(group) >= 2)
        .with_columns(
            (pl.col("annual_return") - pl.col("annual_return").mean().over(group)).alias(
                "return_gap"
            ),
            (pl.col("fee") - pl.col("fee").mean().over(group)).alias("fee_gap"),
        )
        .select("series_id", "return_year", "class_id", "return_gap", "fee_gap")
    )


def fit(gaps: pl.DataFrame) -> Slope:
    """Slope through the origin: both gaps average zero within every fund-year."""
    x = gaps["fee_gap"].to_numpy()
    y = gaps["return_gap"].to_numpy()
    groups = gaps["series_id"].cast(pl.Categorical).to_physical().to_numpy()
    model = sm.OLS(y, x).fit(cov_type="cluster", cov_kwds={"groups": groups})
    low, high = model.conf_int()[0]
    return Slope(
        slope=float(model.params[0]),
        low=float(low),
        high=float(high),
        p_value=float(model.pvalues[0]),
        observations=len(y),
        funds=int(gaps["series_id"].n_unique()),
        fund_years=int(gaps.select(pl.struct("series_id", "return_year").n_unique()).item()),
    )


def binned(
    gaps: pl.DataFrame, width: float = BIN_WIDTH, limit: float = MAX_FEE_GAP
) -> pl.DataFrame:
    """Average return gap per fee-gap bin, for plotting.

    Rows are sorted and grouped in order so the means are summed identically on
    every run, and a rounded -0.0 is replaced by 0.0 so the zero bin is always
    written the same way.
    """
    bin_ = ((pl.col("fee_gap") / width).round(0) * width).round(6)
    return (
        gaps.filter(pl.col("fee_gap").abs() <= limit)
        .sort("series_id", "return_year", "class_id")
        .with_columns(pl.when(bin_ == 0).then(0.0).otherwise(bin_).alias("fee_gap_bin"))
        .group_by("fee_gap_bin", maintain_order=True)
        .agg(
            pl.len().alias("observations"),
            pl.col("return_gap").mean().alias("mean_return_gap"),
        )
        .filter(pl.col("observations") >= MIN_BIN_OBSERVATIONS)
        .sort("fee_gap_bin")
    )


def analyze(con: duckdb.DuckDBPyConnection) -> tuple[dict, pl.DataFrame]:
    results, main_gaps = {}, None
    for name in SPECIFICATIONS:
        gaps = deviations(con, name).filter(
            pl.col("fee_gap").is_finite() & pl.col("return_gap").is_finite()
        )
        results[name] = asdict(fit(gaps))
        if name == MAIN:
            main_gaps = gaps
    return {"main": MAIN, "specifications": results}, binned(main_gaps)
