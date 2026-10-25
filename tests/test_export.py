"""Tableau tables: percent conversion and stable output."""

import polars as pl

from funds.export import percent, tableau_tables


def test_percent_converts_only_named_columns():
    table = pl.DataFrame({"year": [2016], "median": [0.0101]})
    out = percent(table, ["median", "missing"])
    assert out["median"].item() == 1.01
    assert out["year"].item() == 2016


def test_tableau_tables_are_sorted_on_stable_keys():
    quintiles = pl.DataFrame(
        {
            "horizon_years": [10, 5, 5],
            "fee_quintile": [1, 2, 1],
            "share_beating": [0.3, 0.2, 0.4],
        }
    )
    empty = pl.DataFrame({"x": [1]})
    tables = {
        "share_classes": empty,
        "fund_families": empty,
        "fee_trend": empty,
        "fee_quintiles": quintiles,
        "within_fund_bins": empty,
        "survivorship": empty,
    }
    out = tableau_tables(tables)["fee_quintiles"]
    assert out.select("horizon_years", "fee_quintile").rows() == [(5, 1), (5, 2), (10, 1)]
    assert out["share_beating"].to_list() == [40.0, 20.0, 30.0]
