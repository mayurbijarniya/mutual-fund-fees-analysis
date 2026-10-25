"""Figures written by hand in the README must match results.json."""

import json

import pytest

from funds import paths, report

README = paths.ROOT / "README.md"


@pytest.fixture(scope="module")
def results():
    if not paths.RESULTS.exists():
        pytest.skip("outputs/results.json not built; run `funds analyze`")
    return json.loads(paths.RESULTS.read_text())


@pytest.fixture(scope="module")
def readme():
    return README.read_text()


def test_share_classes(results, readme):
    assert f"{results['data']['share_classes']:,} mutual fund share classes" in readme


def test_fee_trend(results, readme):
    fees = results["fees"]
    same = fees["same_class_change"]
    first = next(r for r in fees["by_year"] if r["year"] == same["start_year"])
    last = next(r for r in fees["by_year"] if r["year"] == same["end_year"])
    assert f"**{report.pct(first['median'], 2)}** ({same['start_year']})" in readme
    assert f"**{report.pct(last['median'], 2)}** ({same['end_year']})" in readme
    assert f"{report.pct(same['median_start'], 2)} to {report.pct(same['median_end'], 2)}" in readme


def test_within_fund_slope(results, readme):
    q2 = results["within_fund"]["specifications"][results["within_fund"]["main"]]
    assert f"**{-q2['slope']:.2f} points less**" in readme
    assert f"{-q2['high']:.2f} to {-q2['low']:.2f}" in readme


def test_benchmark_shares(results, readme):
    five = results["benchmark"]["5_year"]
    cheap, dear = five["by_quintile"][0], five["by_quintile"][-1]
    assert f"**{report.pct(five['share_beating'])}**" in readme
    assert f"**{report.pct(cheap['share_beating'])}**" in readme
    assert f"**{report.pct(dear['share_beating'])}**" in readme
    fee_gap = dear["median_fee"] - cheap["median_fee"]
    gross_gap = dear["median_excess_before_fees"] - cheap["median_excess_before_fees"]
    assert f"charges {fee_gap * 100:.2f} points more" in readme
    assert f"only {gross_gap * 100:.2f} points more before fees" in readme


def test_survivorship(results, readme):
    q4 = results["survivorship"]
    assert f"**{report.pct(q4['cohort_2016']['share_stopped'])}**" in readme
    assert f"**{q4['mean_yearly_bias'] * 100:.2f} points**" in readme
