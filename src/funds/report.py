"""Render reports/FINDINGS.md from results.json.

Every number in the findings is read from the analysis output at render time,
so re-running the pipeline cannot leave a stale figure behind in the prose.
"""

from __future__ import annotations

from funds import paths


def pct(x: float, digits: int = 1) -> str:
    return f"{x * 100:.{digits}f}%"


def pts(x: float, digits: int = 2) -> str:
    """A difference of rates, in percentage points."""
    return f"{x * 100:+.{digits}f}"


def _year(rows: list[dict], year: int) -> dict:
    return next(r for r in rows if r["year"] == year)


def _status(rows: list[dict], status: str) -> dict:
    return next(r for r in rows if r["status"] == status)


QUINTILE_HEADER = (
    "| Fee quintile | Fee range | Share classes | Beat their index | Median excess "
    "| Median excess before fees |\n|---|---|---|---|---|---|"
)


def _quintile_rows(rows: list[dict]) -> str:
    return "\n".join(
        f"| Q{r['fee_quintile']} | {pct(r['min_fee'], 2)} to {pct(r['max_fee'], 2)} | "
        f"{r['share_classes']:,} | {pct(r['share_beating'])} "
        f"[{pct(r['share_beating_low'])}, {pct(r['share_beating_high'])}] | "
        f"{pts(r['median_excess'])} | {pts(r['median_excess_before_fees'])} |"
        for r in rows
    )


def build(results: dict) -> str:
    data = results["data"]
    fees = results["fees"]
    same = fees["same_class_change"]
    first = _year(fees["by_year"], same["start_year"])
    last = _year(fees["by_year"], same["end_year"])
    active = _status(fees["by_status"], "active")
    stopped = _status(fees["by_status"], "stopped filing")

    q2 = results["within_fund"]
    main = q2["specifications"][q2["main"]]
    specs = "\n".join(
        f"| {name.replace('_', ' ')} | {s['slope']:.2f} [{s['low']:.2f}, {s['high']:.2f}] | "
        f"{s['observations']:,} | {s['funds']:,} |"
        for name, s in q2["specifications"].items()
    )

    q3 = results["benchmark"]
    five, ten = q3["5_year"], q3["10_year"]
    index_5 = next(r for r in five["by_index_fund"] if r["index_fund"])
    active_5 = next(r for r in five["by_index_fund"] if not r["index_fund"])
    cheap, dear = five["by_quintile"][0], five["by_quintile"][-1]
    cheap_10, dear_10 = ten["by_quintile"][0], ten["by_quintile"][-1]
    fee_gap = dear["median_fee"] - cheap["median_fee"]
    gross_gap = dear["median_excess_before_fees"] - cheap["median_excess_before_fees"]
    gross_gap_10 = dear_10["median_excess_before_fees"] - cheap_10["median_excess_before_fees"]
    fee_gap_10 = dear_10["median_fee"] - cheap_10["median_fee"]
    headline_fall = first["median"] - last["median"]
    same_class_fall = same["median_start"] - same["median_end"]

    q4 = results["survivorship"]
    cohort = q4["cohort_2016"]
    by_status = {(r["horizon_years"], r["status"]): r for r in q4["benchmark_by_status"]}
    surv_5, gone_5 = by_status[(5, "active")], by_status[(5, "stopped filing")]
    y0, y1 = q4["years"]

    return f"""# Findings

Generated from `outputs/results.json` by `funds analyze`. Do not edit by hand:
re-run the pipeline instead.

**Data:** {data["quarters"]} quarterly SEC prospectus datasets, {data["first_quarter"]} to
{data["last_quarter"]}: {data["filings"]:,} filings and {data["facts"]:,} fee and return
facts, covering {data["share_classes"]:,} share classes in {data["funds"]:,} funds
({data["tickers"]:,} with a ticker). {pct(data["restated_disagree"])} of the
{data["class_years"]:,} class-year returns differ between the prospectuses that restate
them; {data["invalid_expense_ratios"]:,} of {data["expense_ratio_rows"]:,} expense ratios
were outside 0 to 10% and excluded.

## Q1. What funds charge

The median share class's effective expense ratio fell from {pct(first["median"], 2)} in
{first["year"]} to {pct(last["median"], 2)} in {last["year"]}.

Most of that {headline_fall * 100:.2f}-point fall came from **which funds exist**, not
from funds cutting their prices. The {same["classes"]:,} share classes that filed in both
years went from a median of {pct(same["median_start"], 2)} to
{pct(same["median_end"], 2)}, a fall of only {same_class_fall * 100:.2f} points; the
typical class changed its fee by {pts(same["median_change"])} points.
{pct(same["share_cut"], 0)} cut their fee and {pct(same["share_raised"], 0)} raised it.
The rest of the decline is cheaper funds launching and more expensive ones
closing: share classes that stopped filing had a median fee of
{pct(stopped["median_expense_ratio"], 2)}, against {pct(active["median_expense_ratio"], 2)}
for those still filing.

![Fee trend](../outputs/figures/fee_trend.png)

## Q2. Fees come out of returns

Share classes of the same fund hold the same portfolio. Within a fund and year, a class
charging one percentage point more returned **{-main["slope"]:.2f} points less**
(95% interval {-main["high"]:.2f} to {-main["low"]:.2f}), across {main["observations"]:,}
class-years in {main["funds"]:,} funds.

| Fee matched to the return | Slope [95% interval] | Class-years | Funds |
|---|---|---|---|
{specs}

The main specification takes the fee from the prospectus filed the following year,
which reports that year's actual expenses. A class's typical fee across all years is a
noisier measure of what it charged in a given year, which pulls the slope toward zero.
The remaining gap from -1 is consistent with the prospectus fee being a stated ratio
rather than the exact cost charged that year.

![Within-fund fees and returns](../outputs/figures/within_fund.png)

## Q3. Expensive funds beat their index less often

Each share class against the one index its own prospectus names, latest comparison per
class:

- **5 years:** {pct(five["share_beating"])} of {five["share_classes"]:,} share classes
  beat their index (95% interval {pct(five["share_beating_low"])} to
  {pct(five["share_beating_high"])}); median excess return {pts(five["median_excess"])}
  points a year.
- **10 years:** {pct(ten["share_beating"])} of {ten["share_classes"]:,}; median excess
  return {pts(ten["median_excess"])} points a year.

By fee quintile, 5 years:

{QUINTILE_HEADER}
{_quintile_rows(five["by_quintile"])}

The cheapest fifth beat its index {pct(cheap["share_beating"])} of the time and the most
expensive fifth {pct(dear["share_beating"])}. **Higher fees do not buy matching
results.** The most expensive fifth charges {fee_gap * 100:.2f} points a year more than
the cheapest, but before fees it did only {gross_gap * 100:.2f} points better over 5
years ({gross_gap_10 * 100:.2f} better over 10, against a fee gap of
{fee_gap_10 * 100:.2f}). Most of the extra fee is a straight loss to the investor. On
average across share classes (a regression, so the highest fees weigh in more than in
the medians above), each extra point of fee went with
{-five["fee_slope"]["slope"]:.2f} points less excess return a year (95% interval
{-five["fee_slope"]["high"]:.2f} to {-five["fee_slope"]["low"]:.2f}).

Index funds beat their index {pct(index_5["share_beating"])} of the time
({index_5["share_classes"]:,} share classes), with a median excess return of
{pts(index_5["median_excess"])} points against a median fee of
{pct(index_5["median_fee"], 2)}: they track their index minus their cost, as designed.
Other funds beat theirs {pct(active_5["share_beating"])} of the time.

10 years:

{QUINTILE_HEADER}
{_quintile_rows(ten["by_quintile"])}

![Beating the index by fee quintile](../outputs/figures/benchmark_quintiles.png)

## Q4. Survivorship

Of the {cohort["share_classes"]:,} share classes filing in 2016, {cohort["stopped"]:,}
({pct(cohort["share_stopped"])}) had stopped filing by the end of the data. They charged
more: a median of {pct(cohort["fee_stopped"], 2)} against {pct(cohort["fee_active"], 2)}
for the survivors.

Averaging only the classes that survived overstates the average yearly return by
**{q4["mean_yearly_bias"] * 100:.2f} percentage points a year** ({y0} to {y1}). Over
5 years, {pct(surv_5["share_beating"])} of surviving classes beat their index, against
{pct(gone_5["share_beating"])} of those that stopped filing.

![Survivorship bias by year](../outputs/figures/survivorship.png)

## Limits

- **Equal-weighted.** The filings carry no fund sizes, so every figure is per share class,
  not per dollar invested. Large, cheap index funds hold most of the money.
- **The fund chooses its benchmark.** A fund may pick an index that flatters it.
- **Stopping filing is not always failure.** Classes also disappear when they merge,
  convert into another class or are renamed.
- **One benchmark only.** Funds listing two or more indexes on the same date are left out
  of Q3 rather than matched by guesswork.
- **2026 is partial.** Fee figures for 2026 cover filings to mid-year only.

## Sources

- [SEC Mutual Fund Prospectus Risk/Return Summary Data Sets](https://www.sec.gov/data-research/sec-markets-data/mutual-fund-prospectus-riskreturn-summary-data-sets)
- [SEC field documentation](https://www.sec.gov/dera/data/rr1.pdf)
- [SEC Investment Company Series and Class Information](https://www.sec.gov/data-research/sec-markets-data/investment-company-series-class-information)
"""


def render(results: dict) -> None:
    paths.FINDINGS.parent.mkdir(parents=True, exist_ok=True)
    paths.FINDINGS.write_text(build(results))
