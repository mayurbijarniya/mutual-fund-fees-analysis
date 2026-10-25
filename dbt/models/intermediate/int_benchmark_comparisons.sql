-- Share class average returns against the market index named in the same
-- prospectus, for 5 and 10 years.
--
-- rr filings only: oef does not label which average is which. A comparison is
-- made only when the prospectus lists exactly one index for the fund on that
-- date; with two or more, picking one would be a guess.

with fund_rows as (
    select
        accession_number,
        series_id,
        class_id,
        period_end,
        filed_date,
        tag,
        median(value) as fund_return
    from {{ ref('int_facts_dated') }}
    where taxonomy = 'rr'
      and tag in ('AverageAnnualReturnYear05', 'AverageAnnualReturnYear10')
      and class_id is not null
      and (measure is null or lower(measure) not like '%after%')
    group by all
),

index_rows as (
    select
        accession_number,
        series_id,
        period_end,
        tag,
        count(distinct measure)     as indexes_listed,
        any_value(measure)          as benchmark_name,
        median(value)               as benchmark_return
    from {{ ref('int_facts_dated') }}
    where taxonomy = 'rr'
      and tag in ('AverageAnnualReturnYear05', 'AverageAnnualReturnYear10')
      and class_id is null
      and measure is not null
      and series_id is not null
    group by all
)

select
    f.accession_number,
    f.series_id,
    f.class_id,
    f.period_end,
    f.filed_date,
    case f.tag when 'AverageAnnualReturnYear05' then 5 else 10 end     as horizon_years,
    f.fund_return,
    i.benchmark_return,
    i.benchmark_name,
    f.fund_return - i.benchmark_return                                  as excess_return
from fund_rows f
join index_rows i using (accession_number, series_id, period_end, tag)
where i.indexes_listed = 1
