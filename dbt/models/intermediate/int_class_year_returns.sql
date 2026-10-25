-- One return per share class per year, taken from the most recently filed
-- prospectus. `reports` and `distinct_values` record how many filings stated
-- that year and whether they agreed, as a data quality measure.
--
-- A single filing can state the same class's return more than once, in
-- different documents. Those rows tie on every ordering key, so each filing is
-- first reduced to one value (the median) before the latest filing is chosen;
-- otherwise every build could keep a different row.

with per_filing as (
    select
        accession_number,
        class_id,
        return_year,
        any_value(filed_date)       as filed_date,
        any_value(taxonomy)         as taxonomy,
        median(annual_return)       as annual_return
    from {{ ref('int_annual_returns') }}
    where return_year between {{ var('first_return_year') }} and {{ var('last_return_year') }}
    group by 1, 2, 3
),

ranked as (
    select
        *,
        row_number() over (
            partition by class_id, return_year
            order by filed_date desc, accession_number desc
        )                                                           as recency,
        count(*) over (partition by class_id, return_year)          as reports,
        count(distinct round(annual_return, 4))
            over (partition by class_id, return_year)               as distinct_values
    from per_filing
)

select
    class_id,
    return_year,
    annual_return,
    accession_number,
    filed_date,
    taxonomy,
    reports,
    distinct_values,
    annual_return between {{ var('min_annual_return') }} and {{ var('max_annual_return') }}
                                                                    as is_valid
from ranked
where recency = 1
