"""Q3: do expensive funds beat their benchmark?

Each share class is compared with the one index its own prospectus names, over
5 and 10 years, using its latest comparison so no class counts twice. Share
classes are split into fee quintiles. Adding each class's fee back to its
excess return gives its result before fees: if higher fees bought better
management, that figure would rise with the fee.
"""

from __future__ import annotations

import duckdb
import numpy as np
import polars as pl
import statsmodels.api as sm
from statsmodels.stats.proportion import proportion_confint

from funds.db import frame

QUINTILES = 5


def comparisons(con: duckdb.DuckDBPyConnection, horizon: int) -> pl.DataFrame:
    return frame(
        con,
        """
        SELECT b.class_id, b.series_id, b.excess_return, b.excess_before_fees,
               b.median_expense_ratio AS fee, b.status, b.benchmark_name,
               coalesce(f.fund_name ILIKE '%index%', false) AS index_fund
        FROM fct_benchmark_excess b
        LEFT JOIN dim_fund f USING (series_id)
        WHERE b.horizon_years = ?
        ORDER BY b.class_id
        """,
        [horizon],
    )


def with_quintiles(table: pl.DataFrame, buckets: int = QUINTILES) -> pl.DataFrame:
    """Fee quintile 1 is the cheapest fifth of share classes.

    Many classes charge exactly the same fee. Ordinal ranking breaks those ties
    by row order, so callers pass rows sorted by class ID to make the split
    the same on every run.
    """
    rank = table["fee"].rank("ordinal").to_numpy()
    quintile = np.ceil(rank * buckets / len(rank)).astype(int)
    return table.with_columns(pl.Series("fee_quintile", quintile))


def share_beating(beat: int, total: int) -> tuple[float, float, float]:
    low, high = proportion_confint(beat, total, alpha=0.05, method="wilson")
    return beat / total, float(low), float(high)


def summary(table: pl.DataFrame, by: str) -> pl.DataFrame:
    rows = []
    for (key,), part in table.group_by([by], maintain_order=True):
        beat = int((part["excess_return"] > 0).sum())
        share, low, high = share_beating(beat, part.height)
        rows.append(
            {
                by: key,
                "share_classes": part.height,
                "min_fee": float(part["fee"].min()),
                "median_fee": float(part["fee"].median()),
                "max_fee": float(part["fee"].max()),
                "share_beating": share,
                "share_beating_low": low,
                "share_beating_high": high,
                "median_excess": float(part["excess_return"].median()),
                "mean_excess": float(part["excess_return"].mean()),
                "median_excess_before_fees": float(part["excess_before_fees"].median()),
            }
        )
    return pl.DataFrame(rows).sort(by)


def fee_slope(table: pl.DataFrame) -> dict:
    """Excess return on fee, with fund-clustered errors. -1 means fees are pure cost."""
    x = sm.add_constant(table["fee"].to_numpy())
    groups = table["series_id"].cast(pl.Categorical).to_physical().to_numpy()
    model = sm.OLS(table["excess_return"].to_numpy(), x).fit(
        cov_type="cluster", cov_kwds={"groups": groups}
    )
    low, high = model.conf_int()[1]
    return {
        "slope": float(model.params[1]),
        "low": float(low),
        "high": float(high),
        "p_value": float(model.pvalues[1]),
        "observations": table.height,
    }


def analyze(con: duckdb.DuckDBPyConnection) -> tuple[dict, pl.DataFrame]:
    results, tables = {}, []
    for horizon in (5, 10):
        table = with_quintiles(comparisons(con, horizon))
        beat = int((table["excess_return"] > 0).sum())
        share, low, high = share_beating(beat, table.height)
        by_quintile = summary(table, "fee_quintile")
        results[f"{horizon}_year"] = {
            "share_classes": table.height,
            "funds": table["series_id"].n_unique(),
            "share_beating": share,
            "share_beating_low": low,
            "share_beating_high": high,
            "median_excess": float(table["excess_return"].median()),
            "fee_slope": fee_slope(table),
            "by_quintile": by_quintile.to_dicts(),
            "by_index_fund": summary(table, "index_fund").to_dicts(),
        }
        tables.append(by_quintile.with_columns(pl.lit(horizon).alias("horizon_years")))
    return results, pl.concat(tables)
