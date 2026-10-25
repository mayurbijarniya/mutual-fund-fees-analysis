"""Fee quintiles, index-beating shares and the fee slope, on known inputs."""

import numpy as np
import polars as pl
import pytest

from funds.benchmark import fee_slope, share_beating, summary, with_quintiles


def classes(n=1000, slope=-1.0, seed=1):
    rng = np.random.default_rng(seed)
    fee = rng.uniform(0.0005, 0.02, n)
    excess = slope * fee + rng.normal(0, 0.01, n)
    return pl.DataFrame(
        {
            "class_id": [f"C{i}" for i in range(n)],
            "series_id": [f"S{i // 3}" for i in range(n)],
            "fee": fee,
            "excess_return": excess,
            "excess_before_fees": excess + fee,
        }
    )


def test_quintiles_are_equal_sized_and_ordered_by_fee():
    table = with_quintiles(classes(1000))
    sizes = table.group_by("fee_quintile").len().sort("fee_quintile")["len"].to_list()
    assert sizes == [200] * 5
    by_q = table.group_by("fee_quintile").agg(pl.col("fee").max()).sort("fee_quintile")
    assert by_q["fee"].is_sorted()


def test_quintile_one_is_the_cheapest():
    table = with_quintiles(classes(500))
    cheapest = table.filter(pl.col("fee") == pl.col("fee").min())
    assert cheapest["fee_quintile"].item() == 1


def test_share_beating_interval_brackets_the_share():
    share, low, high = share_beating(30, 100)
    assert share == 0.3
    assert low < 0.3 < high
    assert low >= 0 and high <= 1


def test_summary_counts_and_shares():
    table = with_quintiles(classes(1000))
    rows = summary(table, "fee_quintile").to_dicts()
    assert [r["fee_quintile"] for r in rows] == [1, 2, 3, 4, 5]
    assert sum(r["share_classes"] for r in rows) == 1000
    for r in rows:
        assert r["share_beating_low"] <= r["share_beating"] <= r["share_beating_high"]


def test_fee_slope_recovers_a_known_drag():
    result = fee_slope(classes(5000, slope=-1.0))
    assert result["slope"] == pytest.approx(-1.0, abs=0.1)
    assert result["low"] < -1.0 < result["high"]
