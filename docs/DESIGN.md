# Design

Written after profiling the data and before any analysis code, so the questions
and rules are fixed before the answers are known.

## Data

**SEC Mutual Fund Prospectus Risk/Return Summary Data Sets**, quarterly, from
`sec.gov/files/dera/data/mutual-fund-prospectus-risk/return-summary-data-sets/`.
Every mutual fund prospectus must open with a standard summary: a fee table, a
bar chart of yearly returns, and a table of average returns against a market
index. The SEC publishes those numbers as structured data.

| | |
|---|---|
| Quarters used | 42, from 2016 Q1 to 2026 Q2 (downloaded 2026-10-22) |
| Raw size | 1.3 GB zipped |
| Facts kept | 7.55 million fee and return values (33 MB as Parquet) |
| Share classes with a fee | 57,907, in 22,429 funds |
| Names and tickers | SEC "Investment Company Series and Class Information", one list per year, 2017 to 2026 |

A **fund** (SEC "series") is one portfolio. A **share class** is one way of
owning it: the same holdings, sold with different fees (an institutional class
and a retail class of the same fund, for example).

### What profiling found

- **Two vocabularies.** Filings used the `rr` taxonomy until 2025 and its
  successor `oef` from 2024; 2026 filings are entirely `oef`. The share class
  sits in its own column in `rr` and inside a dimension string in `oef`; yearly
  returns carry the year in the tag name in `rr` (`AnnualReturn2014`) and in
  the period date in `oef` (`AnnlRtrPct`). Both are merged into one model.
- **Other products file under other taxonomies.** Variable insurance products
  (`vip`) and closed-end funds (`cef`) are excluded: their fee tables measure
  something different.
- **Typing errors.** 4,526 of 474,309 gross expense ratios exceed 10%, and 537
  exceed 100%: values typed in percent ("1.02") where a fraction was expected.
- **Empty values.** 89,285 facts have no value, for example a 10-year return for
  a fund younger than ten years.
- **Average returns are only usable in `rr`.** In `oef` the 1, 5 and 10 year
  averages share a tag and date and cannot be told apart from the published
  columns. Long-run performance is therefore computed from yearly returns, and
  the benchmark comparison uses `rr` filings.
- **Benchmarks are not always unique.** 48% of fund filings list exactly one
  index; the rest list two to eight (a broad index plus a style index, often).
- **No fund assets.** The data has no fund sizes, so every average is per share
  class (equal-weighted), not per dollar invested.

## Questions

**Q1. What do funds charge, and how has it changed?**
The effective expense ratio of each share class in each prospectus year,
2016 to 2026: the net ratio after fee waivers where one is reported, otherwise
the gross ratio. Reported as the median and the distribution.

**Q2. Do fees come straight out of returns?**
Share classes of the same fund hold the same portfolio and differ in fees, so
within a fund and year, a class charging one percentage point more should
return one point less. Pooled regression of each class's return, relative to
its fund's average that year, on its fee relative to the fund's average. The
expected slope is -1. Standard errors are clustered by fund.

*Revised after the first run.* The first version used each class's typical fee
across all its years and gave a slope of -0.77. A typical fee is a noisy
measure of the fee charged in a given year, and noise in the explanatory
variable biases a slope toward zero. The main specification now uses the fee in
the prospectus filed the following year, which reports that year's actual
expenses. The typical-fee and same-year versions are kept as robustness checks,
so the change is visible rather than hidden.

**Q3. Do expensive funds beat their benchmark?**
Each share class's 5 and 10 year average return against the one market index
its prospectus compares it with, from its latest `rr` filing. Share of classes
that beat their index, and the average excess return, by fee quintile. Adding
the fee back gives the return before fees: if expensive funds were buying
skill, it would rise with the fee.

**Q4. How much does survivorship flatter the averages?**
Funds that close or merge stop filing and drop out of any dataset built from
today's funds. A share class is **active** if it appears in a filing in the
last four quarters (2025 Q3 to 2026 Q2), otherwise **stopped filing**. Compare
the yearly average return of all classes with that of survivors only, and the
fees and benchmark results of the two groups.

## Rules

| Rule | Value | Why |
|---|---|---|
| Valid expense ratio | 0 to 10% | larger values are unit errors |
| Valid yearly return | -95% to +300% | outside this is a data error |
| Return years | 2006 to 2025 | earliest and latest complete years in the filings |
| One return per class and year | from the most recently filed prospectus | the same year is restated in up to ten prospectuses |
| Before-tax returns only | exclude any measure containing "after" | after-tax rows are labeled at least six ways |
| Benchmark match | the filing lists exactly one index for that fund | anything else is a guess |
| Fee quintiles | across share classes, by median effective expense ratio | |
| Active | filed in the last four quarters | |

## What this does not claim

- **Not asset-weighted.** Without fund sizes, the typical share class is not the
  typical dollar.
- **Not every fund.** Exchange-traded funds and mutual funds that file the
  summary are included; insurance products and closed-end funds are not.
- **Stopping filing is not failure.** Classes also disappear when they merge,
  convert into another class or are renamed.
- **The benchmark is the fund's own choice.** Funds pick the index they compare
  themselves with, which can flatter them.
