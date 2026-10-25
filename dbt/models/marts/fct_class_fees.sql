-- Effective expense ratio per share class per prospectus year (the year the
-- prospectus was filed). Invalid ratios are excluded.

select
    e.class_id,
    c.series_id,
    year(e.filed_date)                  as prospectus_year,
    median(e.effective_expense_ratio)   as effective_expense_ratio,
    median(e.gross_expense_ratio)       as gross_expense_ratio,
    bool_or(e.net_expense_ratio is not null and e.net_expense_ratio < e.gross_expense_ratio)
                                        as has_fee_waiver,
    count(*)                            as filings
from {{ ref('int_expense_ratios') }} e
join {{ ref('dim_share_class') }} c using (class_id)
where e.is_valid
group by 1, 2, 3
