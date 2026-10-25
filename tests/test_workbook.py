"""The Tableau workbook: plain sheets in order, and tiles that match the results."""

import json
import re
import zipfile
from datetime import date

import polars as pl
import pytest

from funds import export, paths


def sheet_names(path):
    with zipfile.ZipFile(path) as zf:
        return re.findall(r'<sheet name="([^"]+)"', zf.read("xl/workbook.xml").decode())


def test_workbook_has_plain_sheets_in_order(tmp_path):
    sheets = {"share_classes": pl.DataFrame({"a": [1]}), "kpis": pl.DataFrame({"b": ["x"]})}
    path = export.write_workbook(sheets, date(2026, 6, 30), tmp_path)
    assert sheet_names(path) == ["about", "share_classes", "kpis"]
    with zipfile.ZipFile(path) as zf:
        assert not [n for n in zf.namelist() if n.startswith("xl/tables/")]


def test_workbook_is_identical_on_rewrite(tmp_path):
    sheets = {"share_classes": pl.DataFrame({"a": [1.5, None], "b": [True, False]})}
    first = export.write_workbook(sheets, date(2026, 6, 30), tmp_path / "one").read_bytes()
    second = export.write_workbook(sheets, date(2026, 6, 30), tmp_path / "two").read_bytes()
    assert first == second


@pytest.fixture(scope="module")
def results():
    if not paths.RESULTS.exists():
        pytest.skip("outputs/results.json not built; run `funds analyze`")
    return json.loads(paths.RESULTS.read_text())


def test_kpi_tiles_quote_the_results(results):
    tiles = {row["kpi"]: row for row in export.kpis(results).iter_rows(named=True)}
    five = results["benchmark"]["5_year"]
    assert tiles["beat_index_5y"]["display"] == f"{five['share_beating'] * 100:.1f}%"
    assert tiles["share_classes"]["value"] == results["data"]["share_classes"]
    stopped = results["survivorship"]["cohort_2016"]["share_stopped"]
    assert tiles["stopped_filing"]["display"] == f"{stopped * 100:.1f}%"


def test_committed_workbook_has_every_sheet():
    path = paths.TABLEAU / "funds_dashboard.xlsx"
    if not path.exists():
        pytest.skip("workbook not built; run `funds analyze`")
    assert sheet_names(path) == [
        "about",
        "share_classes",
        "kpis",
        "fund_families",
        "fee_trend",
        "fee_quintiles",
        "within_fund_bins",
        "survivorship",
    ]
