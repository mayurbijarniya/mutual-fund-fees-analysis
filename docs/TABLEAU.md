# Building the Tableau Public dashboard

Built in the browser with Tableau Public's free web authoring: no install needed.
Everything comes from one file, `outputs/tableau/funds_dashboard.xlsx`, written by
`funds analyze`. Tableau Public saves to your public profile, so everything in the
workbook is public; it is all public SEC data.

Published: [Do Expensive Mutual Funds Earn Their Fees?](https://public.tableau.com/app/profile/mayur.mahavir.bijarniya/viz/DoExpensiveMutualFundsEarnTheirFees/3_Whyaverageslie)

## The plan

| Dashboard | Audience | Answers |
|---|---|---|
| 1. Are fees worth paying? | anyone | the headline numbers and the evidence |
| 2. Look up your fund | an investor | "is my fund's fee worth it?" |
| 3. Why averages lie | an analyst | how fund closures flatter averages |

## The workbook

| Sheet | Rows | One row per | Used for |
|---|---|---|---|
| `about` | 8 | sheet | notes; not used in a view |
| `share_classes` | 57,843 | share class | fee bands, fund lookup, fund families, every calculated field |
| `kpis` | 9 | headline number | the tiles on dashboard 1 |
| `fee_trend` | 11 | prospectus year | fee lines |
| `fee_quintiles` | 10 | quintile and horizon | not used; fee bands tell the same story live |
| `survivorship` | 9 | year | survivorship gap |
| `fund_families` | 96 | fund family | cross-check for the families view |
| `within_fund_bins` | 14 | fee-gap bin | the same-fund chart |

Percent columns are already in percent (0.82 means 0.82%).

## 1. Data sources

1. Sign in at public.tableau.com, open **My Profile**, click **Create a Viz**, and drop
   in `funds_dashboard.xlsx`.
2. Drag `share_classes` onto the canvas. That is the main data source.
3. Add `kpis`, `fee_trend`, `survivorship` and `within_fund_bins` each as their own
   source: **Data** > **New Data Source**, upload the same file, drag the one sheet
   onto an empty canvas, then **Create Extract**. Never drag a second sheet onto an
   existing source's canvas: that relates the two tables.

Selecting a source in the Data pane only changes which fields are listed; pills
already on a sheet keep reading from their own source.

## 2. Calculated fields (on `share_classes`)

| Name | Formula | Why |
|---|---|---|
| `Horizon` | parameter: Integer, list `5` / `10` (shown as 5 years / 10 years), default 5 | one switch for the index charts |
| `Excess (selected)` | `IF [Horizon] = 5 THEN [Excess 5Y Pct] ELSE [Excess 10Y Pct] END` | follows the switch |
| `Beat Index (selected)` | `IF [Horizon] = 5 THEN [Beat Index 5Y] ELSE [Beat Index 10Y] END` | follows the switch |
| `Share Beating` | `AVG(IIF([Beat Index (selected)], 1, 0))` | share of classes beating their index; format as percent |
| `Fee Band` | `IF [Expense Ratio Pct] < 0.25 THEN "1. Under 0.25%" ELSEIF [Expense Ratio Pct] < 0.75 THEN "2. 0.25 to 0.75%" ELSEIF [Expense Ratio Pct] < 1.25 THEN "3. 0.75 to 1.25%" ELSE "4. 1.25% or more" END` | readable fee groups that sort in fee order |
| `Family Median Fee` | `{ FIXED [Fund Family] : MEDIAN([Expense Ratio Pct]) }` | level-of-detail expression; aggregate it with AVG, not SUM |
| `Family Rank` | `RANK([Share Beating])` | table calculation used as the top-15 filter |
| `Search ticker` | duplicate of `Ticker` | a second ticker field for the search box (web authoring opens the existing filter if the same field is dropped twice) |

## 3. Sheets

### Fee bands (share_classes)
- Columns `Fee Band`, Rows `Share Beating`, label on the bars.
- Filters: `Excess (selected)` non-null, `Index Fund` = False.
- Show the `Horizon` parameter.
- Title: "Active funds: the more they charge, the less often they beat their index".

### Fund lookup (share_classes)
- Rows `Ticker`, `Fund Name`, `Class Name`, `Status`; Measure Values `Expense Ratio Pct`,
  `Excess 5Y Pct`, `Excess 10Y Pct`, two decimals, aliased `Fee (%)`, `5 yr vs index`,
  `10 yr vs index`.
- Filters: `Ticker` excluding Null; `Search ticker` wildcard **Contains**, shown as a
  **Wildcard Match** card, default `VFIAX`.
- Blank 5 and 10 year cells mean the prospectus reported no comparison.

### KPI tiles (kpis)
- Filter `Kpi` to one value; `Display` and `Label` on Text; Entire View; title hidden.
  `Display` at 28 bold, `Label` at 11.
- Duplicate for `share_classes`, `beat_index_5y`, `fee_pass_through`, `stopped_filing`.

### Fee trend (fee_trend)
- Columns `Year` (continuous), filter 2016 to 2025 (2026 is half a year).
- Rows `Measure Values` with `Median`, `P25`, `P75`; `Measure Names` on Color, aliased
  `Typical fund (median)`, `Cheapest quarter (25th pct)`, `Priciest quarter (75th pct)`.
- Title: "Fees fell from 1.01% to 0.82%, mostly because cheap funds launched".

### Survivorship (survivorship)
- Columns `Year` (discrete), Rows `Bias` as bars, label two decimals.
- Title: "Counting only surviving funds overstates returns by 0.39 points a year".

### Same fund, different fee (within_fund_bins)
- Columns `Fee Gap Bin` as a continuous **dimension** (as a measure it sums to one dot),
  Rows `Mean Return Gap`, circles sized by `Observations`.
- Title: "Same portfolio, different fee: each extra point of fee costs 0.86 points of return".

### Fund families (share_classes)
- Rows `Fund Family`, Columns `Share Beating`, sorted descending, labelled.
- Filters: `COUNT(Excess (selected))` at least 50, `Index Fund` = False, `Fund Family`
  excluding Null, `Family Rank` 1 to 15.
- Use the rank filter, not a Top 15 filter: Tableau applies Top N before dimension and
  measure filters, so it would pick the top 15 of all families, small ones included.
- Tooltip `AVG(Family Median Fee)`. Show the `Horizon` parameter.
- Title: "The 15 fund families that beat their index most often".

## 4. Dashboards

All three are a fixed 1200 × 900 with floating objects placed by exact position
(Layout tab, x / y / width / height), which is easier to control in web authoring
than tiled containers. Each has a title text box and the footer "Source: SEC
prospectus filings, 2016–2026 · share classes equal-weighted · funds choose their own
benchmark".

| Dashboard | Object | x | y | w | h |
|---|---|---|---|---|---|
| 1. Are fees worth paying? | title | 0 | 0 | 1000 | 80 |
| | Horizon card | 1000 | 15 | 190 | 55 |
| | four KPI tiles | 0, 300, 600, 900 | 80 | 300 | 130 |
| | Fee bands | 0 | 220 | 600 | 610 |
| | Same fund, different fee | 600 | 220 | 600 | 610 |
| 2. Look up your fund | title and hint | 0 | 0 | 1200 | 80 |
| | Search ticker card | 0 | 85 | 300 | 60 |
| | Horizon card | 320 | 85 | 200 | 60 |
| | Fund lookup | 0 | 150 | 780 | 680 |
| | Fund families | 790 | 150 | 410 | 680 |
| 3. Why averages lie | title and summary | 0 | 0 | 1200 | 90 |
| | Fee trend (legend inside the chart) | 0 | 100 | 600 | 730 |
| | Survivorship | 600 | 100 | 600 | 730 |
| all | footer | 0 | 840 | 1200 | 50 |

Filter cards and parameters appear on a dashboard only when the sheet that shows them
is added; if a card is missing, show it on the sheet first, then add the sheet again.

**Action** on dashboard 2 (**Dashboard** > **Actions** > **Add Action** > **Filter**):
source Fund families, run on Select, target Fund lookup, clearing shows all values,
selected field `Fund Family`.

## 5. Publish

1. Clear any selection before publishing: a selected mark is saved with the workbook.
2. Right-click each dashboard tab > **Hide All Sheets**, so only the dashboards show.
3. On the published page, turn on **Show Sheets as Tabs**.

## 6. Screenshots

One per dashboard, taken from the published page, in `docs/screenshots/`:
`01_overview.png`, `02_lookup.png`, `03_survivorship.png`.
