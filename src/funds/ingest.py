"""Turn the SEC's quarterly zip files into two Parquet datasets.

Each quarter's zip holds six tab-separated tables. Two matter here:

- `sub`: one row per filing (accession number, filer, form, filing date).
- `num`: one row per numeric fact (tag, fund series, share class, value).

`num` is filtered on the way in to the fee and return tags this project uses,
from the two mutual fund taxonomies (`rr`, used until the SEC's 2024 change,
and its successor `oef`). Variable insurance products (`vip`) and closed-end
funds (`cef`) file under other taxonomies and are excluded: they are not open-
end mutual funds, and their fee tables measure something different.
"""

from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import duckdb

from funds import paths

TAXONOMIES = ("rr", "oef")

TAGS = (
    r"^(ExpensesOverAssets|NetExpensesOverAssets|ManagementFeesOverAssets"
    r"|DistributionAndService12b1FeesOverAssets|OtherExpensesOverAssets"
    r"|AcquiredFundFeesAndExpensesOverAssets|FeeWaiverOrReimbursementOverAssets"
    r"|MaximumSalesChargeImposedOnPurchasesOverOfferingPrice"
    r"|MaximumDeferredSalesChargeOverOfferingPrice|PortfolioTurnoverRate"
    r"|AnnualReturn(19|20)\d\d|AnnlRtrPct"
    r"|AverageAnnualReturnYear(01|05|10)|AverageAnnualReturnSinceInception|AvgAnnlRtrPct)$"
)

QUARTER = re.compile(r"^(\d{4}q[1-4])_rr1\.zip$")

READ = "read_csv('{path}', delim='\t', header=true, all_varchar=true, quote='', escape='')"


def quarter_of(path: Path) -> str:
    match = QUARTER.match(path.name)
    if not match:
        raise ValueError(f"not an SEC risk/return file: {path.name}")
    return match.group(1)


def convert(archive: Path, facts_dir: Path, subs_dir: Path) -> tuple[int, int]:
    """Write one quarter's filtered facts and submissions. Returns their row counts."""
    quarter = quarter_of(archive)
    facts_dir.mkdir(parents=True, exist_ok=True)
    subs_dir.mkdir(parents=True, exist_ok=True)
    facts_out = facts_dir / f"{quarter}.parquet"
    subs_out = subs_dir / f"{quarter}.parquet"

    work = Path(tempfile.mkdtemp(dir=facts_dir.parent))
    try:
        with zipfile.ZipFile(archive) as zf:
            zf.extract("num.tsv", work)
            zf.extract("sub.tsv", work)

        con = duckdb.connect()
        taxonomies = ", ".join(f"'{t}'" for t in TAXONOMIES)
        con.execute(
            f"""
            COPY (
                SELECT adsh, tag, version, ddate, uom, series, class, measure,
                       document, otherdims, value, '{quarter}' AS quarter
                FROM {READ.format(path=work / "num.tsv")}
                WHERE split_part(version, '/', 1) IN ({taxonomies})
                  AND regexp_matches(tag, '{TAGS}')
            ) TO '{facts_out}' (FORMAT parquet, COMPRESSION zstd)
            """
        )
        con.execute(
            f"""
            COPY (
                SELECT adsh, cik, name, form, filed, '{quarter}' AS quarter
                FROM {READ.format(path=work / "sub.tsv")}
            ) TO '{subs_out}' (FORMAT parquet, COMPRESSION zstd)
            """
        )
        facts = con.execute(f"SELECT count(*) FROM '{facts_out}'").fetchall()[0][0]
        subs = con.execute(f"SELECT count(*) FROM '{subs_out}'").fetchall()[0][0]
        con.close()
        return facts, subs
    finally:
        shutil.rmtree(work, ignore_errors=True)


LOOKUP_COLUMNS = (
    "file_number",
    "cik",
    "entity_name",
    "entity_org_type",
    "series_id",
    "series_name",
    "class_id",
    "class_name",
    "ticker",
)
LOOKUP_YEAR = re.compile(r"series_class_(\d{4})\.csv$")


def lookups(folder: Path = paths.RAW / "series_class", out: Path = paths.LOOKUPS) -> int:
    """Combine the SEC's yearly series and class lists into one Parquet file.

    The yearly files share a column order but not their headers: 2017 opens with
    a title line, 2018 uses short snake_case names, and 2025 onward begins with
    a byte-order mark. Columns are therefore taken by position, and the header
    row is located by content rather than assumed to be the first line.
    """
    import polars as pl

    frames = []
    for path in sorted(folder.glob("series_class_*.csv")):
        year = int(LOOKUP_YEAR.search(path.name).group(1))
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        # Only the real header names the CIK column; 2017's title line also
        # mentions "Series and Class", so matching on that word alone misfires.
        header = next(i for i, line in enumerate(lines[:5]) if "cik" in line.lower())
        table = pl.read_csv(
            path,
            skip_rows=header + 1,
            has_header=False,
            infer_schema=False,
            encoding="utf8-lossy",
            truncate_ragged_lines=True,
        )
        table = table.select(table.columns[: len(LOOKUP_COLUMNS)])
        table.columns = list(LOOKUP_COLUMNS)
        frames.append(table.with_columns(pl.lit(year).alias("list_year")))

    if not frames:
        raise FileNotFoundError(f"no series_class_YYYY.csv files in {folder}")
    combined = pl.concat(frames).with_columns(
        pl.col(c).str.strip_chars().replace({"": None, "[NULL]": None}) for c in LOOKUP_COLUMNS
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    combined.write_parquet(out)
    return combined.height


def run(raw: Path = paths.RAW, overwrite: bool = False) -> list[tuple[str, int, int]]:
    """Convert every quarter found in `raw`, skipping ones already converted."""
    archives = sorted(raw.glob("*_rr1.zip"))
    if not archives:
        raise FileNotFoundError(f"no SEC files in {raw}; see README for the download step")

    done = []
    for archive in archives:
        quarter = quarter_of(archive)
        target = paths.FACTS / f"{quarter}.parquet"
        if target.exists() and not overwrite:
            continue
        facts, subs = convert(archive, paths.FACTS, paths.SUBMISSIONS)
        done.append((quarter, facts, subs))
    return done
