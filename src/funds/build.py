"""Build the dbt warehouse and run every data test.

dbt runs as its own process: in-process it keeps the DuckDB file open, and the
analysis step that follows needs to open it read-only.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from funds import paths


def dbt_executable() -> str:
    """The dbt installed next to this Python, so the project's environment is used."""
    candidate = Path(sys.executable).with_name("dbt")
    return str(candidate) if candidate.exists() else "dbt"


def run(command: str = "build") -> None:
    args = [dbt_executable(), command, "--project-dir", "dbt", "--profiles-dir", "dbt"]
    # The profile and the source locations are relative to the project root.
    result = subprocess.run(args, cwd=paths.ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(f"dbt {command} failed; see the output above")
