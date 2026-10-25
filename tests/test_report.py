"""The findings must render from the committed results and quote them exactly.

Skipped on a fresh clone that has not run the pipeline.
"""

import json

import pytest

from funds import paths, report


@pytest.fixture(scope="module")
def results():
    if not paths.RESULTS.exists():
        pytest.skip("outputs/results.json not built; run `funds analyze`")
    return json.loads(paths.RESULTS.read_text())


def test_findings_render(results):
    text = report.build(results)
    assert "{" not in text, "an unfilled template field survived"


def test_findings_quote_the_results(results):
    text = report.build(results)
    assert f"{results['data']['share_classes']:,}" in text
    assert report.pct(results["benchmark"]["5_year"]["share_beating"]) in text


def test_committed_findings_are_current(results):
    if not paths.FINDINGS.exists():
        pytest.skip("reports/FINDINGS.md not rendered")
    assert paths.FINDINGS.read_text() == report.build(results), "re-run `funds analyze`"
