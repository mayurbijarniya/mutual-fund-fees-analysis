"""Where every input and output lives, relative to the project root."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
FACTS = PROCESSED / "facts"
SUBMISSIONS = PROCESSED / "submissions"
LOOKUPS = PROCESSED / "series_class.parquet"
DB = PROCESSED / "funds.duckdb"

DBT = ROOT / "dbt"

OUTPUTS = ROOT / "outputs"
TABLEAU = OUTPUTS / "tableau"
FIGURES = OUTPUTS / "figures"
RESULTS = OUTPUTS / "results.json"
FINDINGS = ROOT / "reports" / "FINDINGS.md"

SOURCE_URL = (
    "https://www.sec.gov/files/dera/data/mutual-fund-prospectus-risk/return-summary-data-sets"
)
