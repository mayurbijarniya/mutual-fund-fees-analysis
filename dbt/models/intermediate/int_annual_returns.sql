-- Every yearly return as filed, from both taxonomies.
--
-- rr puts the year in the tag name (AnnualReturn2014); oef uses one tag,
-- AnnlRtrPct, and puts the year in the period end date. Only before-tax
-- returns are kept: after-tax rows are labeled in at least six different ways,
-- all containing "after".

select
    accession_number,
    class_id,
    filed_date,
    quarter,
    taxonomy,
    case
        when taxonomy = 'rr' then cast(regexp_extract(tag, '^AnnualReturn([0-9]{4})$', 1) as integer)
        else year(period_end)
    end                                         as return_year,
    value                                       as annual_return
from {{ ref('int_facts_dated') }}
where class_id is not null
  and (
        (taxonomy = 'rr' and regexp_full_match(tag, 'AnnualReturn[0-9]{4}'))
     or (taxonomy = 'oef' and tag = 'AnnlRtrPct')
  )
  and (measure is null or lower(measure) not like '%after%')
