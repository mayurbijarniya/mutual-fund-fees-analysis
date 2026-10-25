"""Tables for the Tableau Public dashboard.

Written two ways: one CSV per table, readable on GitHub, and one Excel workbook
holding every table as a sheet, so the dashboard needs a single upload. Rates
are converted to percent and rounded here. Rows are sorted on stable keys and
the workbook carries a fixed creation date, so re-running the pipeline on the
same data produces byte-identical files.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import duckdb
import polars as pl

from funds import paths
from funds.benchmark import with_quintiles
from funds.db import frame

MIN_FAMILY_CLASSES = 50


def share_classes(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """One row per share class: the fund explorer."""
    table = frame(
        con,
        """
        WITH b5 AS (SELECT * FROM fct_benchmark_excess WHERE horizon_years = 5),
             b10 AS (SELECT * FROM fct_benchmark_excess WHERE horizon_years = 10)
        SELECT c.class_id,
               c.ticker,
               f.fund_name,
               c.class_name,
               f.fund_family,
               c.status,
               c.first_quarter,
               c.last_quarter,
               c.median_expense_ratio                           AS fee,
               coalesce(f.fund_name ILIKE '%index%', false)     AS index_fund,
               b5.benchmark_name                                AS benchmark_5y,
               b5.excess_return                                 AS excess_5y,
               b10.benchmark_name                               AS benchmark_10y,
               b10.excess_return                                AS excess_10y
        FROM dim_share_class c
        LEFT JOIN dim_fund f USING (series_id)
        LEFT JOIN b5 USING (class_id)
        LEFT JOIN b10 USING (class_id)
        WHERE c.median_expense_ratio IS NOT NULL
        ORDER BY c.class_id
        """,
    )
    # Quintiles here rank every share class with a fee; Q3's quintiles rank only
    # the classes compared with an index, so the column name keeps them apart.
    table = with_quintiles(table).rename({"fee_quintile": "fee_quintile_all_classes"})
    return (
        table.with_columns(
            (pl.col("fee") * 100).round(2).alias("expense_ratio_pct"),
            (pl.col("excess_5y") * 100).round(2).alias("excess_5y_pct"),
            (pl.col("excess_10y") * 100).round(2).alias("excess_10y_pct"),
            (pl.col("excess_5y") > 0).alias("beat_index_5y"),
            (pl.col("excess_10y") > 0).alias("beat_index_10y"),
        )
        .drop("fee", "excess_5y", "excess_10y")
        .sort("class_id")
    )


def fund_families(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Fund families with enough share classes compared with an index over 5 years."""
    return frame(
        con,
        f"""
        SELECT f.fund_family,
               count(*)                                         AS share_classes,
               round(100 * median(b.median_expense_ratio), 2)  AS median_expense_ratio_pct,
               round(100 * avg((b.excess_return > 0)::INT), 1) AS share_beating_index_pct,
               round(100 * median(b.excess_return), 2)         AS median_excess_pct
        FROM fct_benchmark_excess b
        JOIN dim_fund f USING (series_id)
        WHERE b.horizon_years = 5 AND f.fund_family IS NOT NULL
        GROUP BY 1
        HAVING count(*) >= {MIN_FAMILY_CLASSES}
        ORDER BY share_classes DESC, fund_family
        """,
    )


def percent(table: pl.DataFrame, columns: list[str], digits: int = 2) -> pl.DataFrame:
    return table.with_columns(
        (pl.col(c) * 100).round(digits) for c in columns if c in table.columns
    )


def tableau_tables(tables: dict[str, pl.DataFrame]) -> dict[str, pl.DataFrame]:
    return {
        "share_classes": tables["share_classes"],
        "fund_families": tables["fund_families"],
        "fee_trend": percent(
            tables["fee_trend"], ["p25", "median", "p75", "mean", "share_with_waiver"]
        ),
        "fee_quintiles": percent(
            tables["fee_quintiles"],
            [
                "min_fee",
                "median_fee",
                "max_fee",
                "share_beating",
                "share_beating_low",
                "share_beating_high",
                "median_excess",
                "mean_excess",
                "median_excess_before_fees",
            ],
        ).sort("horizon_years", "fee_quintile"),
        "within_fund_bins": percent(
            tables["within_fund_bins"], ["fee_gap_bin", "mean_return_gap"], 3
        ),
        "survivorship": percent(
            tables["survivorship"], ["mean_all", "mean_surviving", "mean_stopped", "bias"]
        ),
    }


def kpis(results: dict) -> pl.DataFrame:
    """The headline numbers for the dashboard's tiles, taken from results.json so
    the tiles always match the findings."""
    fees = results["fees"]
    same = fees["same_class_change"]
    first = next(r for r in fees["by_year"] if r["year"] == same["start_year"])
    last = next(r for r in fees["by_year"] if r["year"] == same["end_year"])
    within = results["within_fund"]["specifications"][results["within_fund"]["main"]]
    five = results["benchmark"]["5_year"]
    cheap, dear = five["by_quintile"][0], five["by_quintile"][-1]
    cohort = results["survivorship"]["cohort_2016"]
    bias = results["survivorship"]["mean_yearly_bias"]
    rows = [
        (
            "share_classes",
            "Share classes analyzed",
            results["data"]["share_classes"],
            f"{results['data']['share_classes']:,}",
            "SEC prospectus filings, 2016 to mid-2026",
        ),
        (
            "median_fee_start",
            f"Median fee, {first['year']}",
            round(first["median"] * 100, 2),
            f"{first['median'] * 100:.2f}%",
            "effective expense ratio, per share class",
        ),
        (
            "median_fee_end",
            f"Median fee, {last['year']}",
            round(last["median"] * 100, 2),
            f"{last['median'] * 100:.2f}%",
            "effective expense ratio, per share class",
        ),
        (
            "fee_pass_through",
            "Return lost per extra point of fee",
            round(-within["slope"], 2),
            f"{-within['slope']:.2f} pts",
            "same fund, different share class",
        ),
        (
            "beat_index_5y",
            "Beat their own index, 5 years",
            round(five["share_beating"] * 100, 1),
            f"{five['share_beating'] * 100:.1f}%",
            "latest comparison per share class",
        ),
        (
            "beat_index_cheapest",
            "Cheapest fifth beating its index",
            round(cheap["share_beating"] * 100, 1),
            f"{cheap['share_beating'] * 100:.1f}%",
            f"median fee {cheap['median_fee'] * 100:.2f}%",
        ),
        (
            "beat_index_priciest",
            "Most expensive fifth beating its index",
            round(dear["share_beating"] * 100, 1),
            f"{dear['share_beating'] * 100:.1f}%",
            f"median fee {dear['median_fee'] * 100:.2f}%",
        ),
        (
            "stopped_filing",
            "2016 share classes gone by 2026",
            round(cohort["share_stopped"] * 100, 1),
            f"{cohort['share_stopped'] * 100:.1f}%",
            "closed, merged or converted",
        ),
        (
            "survivorship_bias",
            "Survivors-only overstatement",
            round(bias * 100, 2),
            f"+{bias * 100:.2f} pts a year",
            "average yearly return",
        ),
    ]
    return pl.DataFrame(rows, schema=["kpi", "label", "value", "display", "detail"], orient="row")


# Column notes shown on the workbook's first sheet.
ABOUT = [
    (
        "share_classes",
        "One row per share class. Use for the fund lookup, the scatter plot and "
        "anything computed in Tableau. Percent columns are already in percent.",
    ),
    ("kpis", "Headline numbers for the tiles, matching reports/FINDINGS.md."),
    ("fee_trend", "Median and middle-half expense ratio by prospectus year. 2026 is partial."),
    (
        "fee_quintiles",
        "Share of classes beating their index by fee quintile and horizon, "
        "with 95% Wilson intervals.",
    ),
    (
        "survivorship",
        "Average yearly return over every class against survivors only; "
        "bias = survivors minus all, in points.",
    ),
    ("fund_families", "Fund families with at least 50 share classes compared with an index."),
    ("within_fund_bins", "Return gap against fee gap within a fund, binned, in points."),
    (
        "source",
        "SEC Mutual Fund Prospectus Risk/Return Summary Data Sets and Investment "
        "Company Series and Class Information. Equal-weighted: no fund sizes in the filings.",
    ),
]


def write_workbook(sheets: dict[str, pl.DataFrame], created: date, out: Path) -> Path:
    """Every table as a plain worksheet: a header row, then data.

    Plain sheets rather than Excel tables, because Tableau lists a workbook's
    tables as well as its sheets, which would show every table twice.
    """
    import xlsxwriter

    out.mkdir(parents=True, exist_ok=True)
    path = out / "funds_dashboard.xlsx"
    with xlsxwriter.Workbook(path) as book:
        book.set_properties({"created": datetime.combine(created, datetime.min.time())})
        bold = book.add_format({"bold": True})

        about = book.add_worksheet("about")
        about.write_row(0, 0, ["sheet", "contents"], bold)
        for i, (sheet, text) in enumerate(ABOUT, start=1):
            about.write_row(i, 0, [sheet, text])
        about.set_column(0, 0, 18)
        about.set_column(1, 1, 110)

        for name, table in sheets.items():
            sheet = book.add_worksheet(name)
            sheet.write_row(0, 0, table.columns, bold)
            for i, row in enumerate(table.iter_rows(), start=1):
                sheet.write_row(i, 0, row)
            sheet.freeze_panes(1, 0)
            sheet.set_column(0, len(table.columns) - 1, 16)
    return path


def write(tables: dict[str, pl.DataFrame], results: dict, out: Path = paths.TABLEAU) -> list[Path]:
    """Write the CSVs and the workbook. `results` are the saved, rounded results."""
    out.mkdir(parents=True, exist_ok=True)
    sheets = tableau_tables(tables)
    written = []
    for name, table in sheets.items():
        path = out / f"{name}.csv"
        table.write_csv(path, float_precision=4)
        written.append(path)

    ordered = {"share_classes": sheets["share_classes"], "kpis": kpis(results)}
    ordered |= {k: v for k, v in sheets.items() if k != "share_classes"}
    created = date.fromisoformat(results["data"]["last_filed"])
    written.append(write_workbook(ordered, created, out))
    return written
