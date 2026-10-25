"""Turning SEC zips and yearly fund lists into Parquet, on small synthetic files."""

import re
import zipfile

import duckdb
import polars as pl
import pytest

from funds import ingest

NUM_HEADER = (
    "adsh\ttag\tversion\tddate\tuom\tseries\tclass\tmeasure\tdocument\totherdims\tiprx\tvalue"
)
SUB_HEADER = "adsh\tcik\tname\tform\tfiled"


def num_row(tag, version, value, series="S000000001", cls="C000000001", otherdims=""):
    return "\t".join(
        ["0001-26-1", tag, version, "20251231", "pure", series, cls, "", "", otherdims, "0", value]
    )


def make_zip(path, num_rows):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("num.tsv", "\n".join([NUM_HEADER, *num_rows]) + "\n")
        zf.writestr("sub.tsv", SUB_HEADER + "\n0001-26-1\t1\tA TRUST\t485BPOS\t20260430\n")


@pytest.mark.parametrize(
    ("tag", "kept"),
    [
        ("ExpensesOverAssets", True),
        ("NetExpensesOverAssets", True),
        ("AnnualReturn2014", True),
        ("AnnlRtrPct", True),
        ("AverageAnnualReturnYear05", True),
        ("AvgAnnlRtrPct", True),
        ("ExpenseExampleYear01", False),
        ("AnnualReturn14", False),
        ("CurrentExpensesPercent", False),
    ],
)
def test_tag_filter(tag, kept):
    assert bool(re.match(ingest.TAGS, tag)) is kept


def test_quarter_is_read_from_the_file_name(tmp_path):
    assert ingest.quarter_of(tmp_path / "2024q3_rr1.zip") == "2024q3"
    with pytest.raises(ValueError, match="not an SEC"):
        ingest.quarter_of(tmp_path / "complaints.zip")


def test_convert_keeps_fund_taxonomies_and_fee_tags_only(tmp_path):
    archive = tmp_path / "2026q2_rr1.zip"
    make_zip(
        archive,
        [
            num_row(
                "ExpensesOverAssets", "oef/2025", "0.0100", cls="", otherdims="Class=C000000001;"
            ),
            num_row("AnnualReturn2015", "rr/2012", "0.0911"),
            num_row("ExpensesOverAssets", "vip/2026", "0.0200"),
            num_row("ExpenseExampleYear01", "oef/2025", "102"),
        ],
    )
    facts, subs = ingest.convert(archive, tmp_path / "facts", tmp_path / "subs")
    assert (facts, subs) == (2, 1)

    kept = duckdb.sql(f"SELECT tag, version, quarter FROM '{tmp_path}/facts/2026q2.parquet'").pl()
    assert sorted(kept["version"].to_list()) == ["oef/2025", "rr/2012"]
    assert set(kept["quarter"]) == {"2026q2"}


def test_convert_cleans_up_its_working_files(tmp_path):
    archive = tmp_path / "2026q1_rr1.zip"
    make_zip(archive, [num_row("ExpensesOverAssets", "rr/2012", "0.01")])
    ingest.convert(archive, tmp_path / "out" / "facts", tmp_path / "out" / "subs")
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["facts", "subs"]


ROW = (
    "811-1,0000001,A TRUST,30,S000000001,Growth Fund,C000000001,Class A,ABCDX,"
    "1 MAIN ST,,BOSTON,MA,02115"
)


@pytest.mark.parametrize(
    ("year", "text"),
    [
        (2017, "Open Gov Series and Class List v final,,,,,,,,,,,,,\nrep_file_num,CIK,entity_name,"
               "entity_org_type,series_id,series_name,class_id,class_name,class_ticker_symbol,"
               "street1,street2,city,state_code,zip\n" + ROW),
        (2018, "rep_file_num,CIK,entity_name,entity_org_type,series_id,series_name,class_id,"
               "class_name,class_ticker_symbol,street1,street2,city,state_code,zip\n" + ROW),
        (2025, "﻿Reporting File Number,CIK Number,Entity Name,Entity Org Type,Series ID,"
               "Series Name,Class ID,Class Name,Class Ticker,Address_1,Address_2,City,State,"
               "Zip Code\n" + ROW),
    ],
)  # fmt: skip
def test_lookups_read_every_header_style(tmp_path, year, text):
    folder = tmp_path / "series_class"
    folder.mkdir()
    (folder / f"series_class_{year}.csv").write_text(text, encoding="utf-8")
    out = tmp_path / "lookups.parquet"
    assert ingest.lookups(folder, out) == 1
    row = pl.read_parquet(out).row(0, named=True)
    assert row["series_id"] == "S000000001"
    assert row["class_id"] == "C000000001"
    assert row["ticker"] == "ABCDX"
    assert row["list_year"] == year
