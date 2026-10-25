-- Each share class's latest comparison with its index, per horizon: one row
-- per class and horizon, so no class is counted more than once.

with latest as (
    select
        *,
        row_number() over (
            partition by class_id, horizon_years
            -- series_id and fund_return complete the order: a class filed under
            -- two series in one prospectus would otherwise tie.
            order by period_end desc, filed_date desc, accession_number desc,
                     series_id, fund_return
        ) as recency
    from {{ ref('int_benchmark_comparisons') }}
    where fund_return between {{ var('min_annual_return') }} and {{ var('max_annual_return') }}
      and benchmark_return between {{ var('min_annual_return') }} and {{ var('max_annual_return') }}
)

select
    l.class_id,
    l.series_id,
    l.horizon_years,
    l.period_end,
    l.fund_return,
    l.benchmark_return,
    l.benchmark_name,
    l.excess_return,
    l.excess_return + c.median_expense_ratio    as excess_before_fees,
    c.median_expense_ratio,
    c.status
from latest l
join {{ ref('dim_share_class') }} c using (class_id)
where l.recency = 1
  and c.median_expense_ratio is not null
