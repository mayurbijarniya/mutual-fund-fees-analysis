"""The within-fund regression, on share classes with a known fee pass-through."""

import numpy as np
import polars as pl
import pytest

from funds.within_fund import binned, fit


def synthetic(pass_through, funds=400, years=5, noise=0.002, seed=0):
    """Funds with two to four classes; each class's return falls by pass_through * fee."""
    rng = np.random.default_rng(seed)
    rows = []
    for f in range(funds):
        fees = rng.uniform(0.001, 0.02, rng.integers(2, 5))
        for y in range(years):
            market = rng.normal(0.08, 0.15)
            returns = market - pass_through * fees + rng.normal(0, noise, len(fees))
            for c, (fee, ret) in enumerate(zip(fees, returns, strict=True)):
                rows.append((f"S{f}", 2016 + y, f"C{f}_{c}", ret, fee))
    table = pl.DataFrame(
        rows, schema=["series_id", "return_year", "class_id", "ret", "fee"], orient="row"
    )
    return table.with_columns(
        (pl.col("ret") - pl.col("ret").mean().over("series_id", "return_year")).alias("return_gap"),
        (pl.col("fee") - pl.col("fee").mean().over("series_id", "return_year")).alias("fee_gap"),
    )


@pytest.mark.parametrize("pass_through", [1.0, 0.5])
def test_recovers_a_known_pass_through(pass_through):
    slope = fit(synthetic(pass_through))
    assert slope.slope == pytest.approx(-pass_through, abs=0.03)
    assert slope.low < slope.slope < slope.high
    assert slope.high - slope.low < 0.1


def test_the_market_cancels_out_within_a_fund_year():
    # A huge common market move must not leak into the slope.
    gaps = synthetic(1.0, noise=0.0)
    assert fit(gaps).slope == pytest.approx(-1.0, abs=1e-6)


def test_counts_funds_and_fund_years():
    slope = fit(synthetic(1.0, funds=50, years=3))
    assert slope.funds == 50
    assert slope.fund_years == 150


def test_bins_drop_sparse_cells_and_follow_the_slope():
    table = binned(synthetic(1.0, funds=2000), width=0.002, limit=0.01)
    assert (table["observations"] >= 50).all()
    centre = table.filter(pl.col("fee_gap_bin").abs() <= 0.004)
    slope = np.polyfit(centre["fee_gap_bin"], centre["mean_return_gap"], 1)[0]
    assert slope == pytest.approx(-1.0, abs=0.1)
