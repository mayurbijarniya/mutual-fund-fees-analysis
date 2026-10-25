-- One valid yearly return per share class, with the class's typical fee and
-- status attached for analysis.

select
    r.class_id,
    c.series_id,
    r.return_year,
    r.annual_return,
    r.reports,
    r.distinct_values = 1               as prospectuses_agree,
    c.median_expense_ratio,
    c.status
from {{ ref('int_class_year_returns') }} r
join {{ ref('dim_share_class') }} c using (class_id)
where r.is_valid
