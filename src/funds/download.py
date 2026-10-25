"""Download the SEC files this project uses.

The SEC's fair access policy requires automated requests to identify the
requester with a name and contact email in the User-Agent header, and to stay
under ten requests a second. Requests without one are refused with HTTP 403.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from pathlib import Path

from funds import paths

SERIES_CLASS_URL = "https://www.sec.gov/files/investment/data/other/{folder}/{name}"

# The SEC moved and renamed these files over the years; each year's path as published.
OLD_FOLDER = "investment-company-series-and-class-information"
NEW_FOLDER = "investment-company-series-class-information"
SERIES_CLASS_FILES = {
    **{y: (OLD_FOLDER, f"investment_company_series_class_{y}.csv") for y in range(2017, 2023)},
    2023: (NEW_FOLDER, "investment_company_series_class_2023.csv"),
    2024: (OLD_FOLDER, "investment-company-series-class-2024.csv"),
    2025: (NEW_FOLDER, "investment-company-series-class-2025.csv"),
    2026: (NEW_FOLDER, "investment-company-series-class-2026.csv"),
}

PAUSE_SECONDS = 1.0


def fetch(url: str, target: Path, user_agent: str) -> bool:
    """Download `url` to `target`. Returns False if the SEC has no such file."""
    if target.exists():
        return True
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return False
        raise
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    partial.write_bytes(data)
    partial.rename(target)
    return True


def quarters(first_year: int, last_year: int) -> list[str]:
    return [f"{y}q{q}" for y in range(first_year, last_year + 1) for q in range(1, 5)]


def run(user_agent: str, first_year: int = 2016, last_year: int = 2026) -> list[str]:
    """Fetch every quarterly risk/return file and yearly series list in range."""
    if "@" not in user_agent:
        raise ValueError('the SEC requires a contact email, e.g. "Jane Doe jane@example.com"')

    fetched = []
    for quarter in quarters(first_year, last_year):
        name = f"{quarter}_rr1.zip"
        if fetch(f"{paths.SOURCE_URL}/{name}", paths.RAW / name, user_agent):
            fetched.append(name)
        time.sleep(PAUSE_SECONDS)

    for year, (folder, name) in SERIES_CLASS_FILES.items():
        if not first_year - 1 <= year <= last_year:
            continue
        target = paths.RAW / "series_class" / f"series_class_{year}.csv"
        if fetch(SERIES_CLASS_URL.format(folder=folder, name=name), target, user_agent):
            fetched.append(target.name)
        time.sleep(PAUSE_SECONDS)
    return fetched
