-- Facts joined to the date their filing was submitted, which orders restated
-- values: the same year's return can appear in up to ten prospectuses.

select
    f.*,
    s.filed_date,
    s.form
from {{ ref('stg_facts') }} f
join {{ ref('stg_submissions') }} s using (accession_number)
where f.value is not null
