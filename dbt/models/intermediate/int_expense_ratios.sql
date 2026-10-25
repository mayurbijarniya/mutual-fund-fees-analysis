-- One expense ratio per share class per filing.
--
-- The effective ratio is what an investor pays: the net ratio after any fee
-- waiver where the prospectus reports one, otherwise the gross ratio. A filing
-- can state a class's ratio in more than one document; the median is taken.

with ratios as (
    select
        accession_number,
        class_id,
        any_value(filed_date)                                           as filed_date,
        any_value(quarter)                                              as quarter,
        median(value) filter (where tag = 'ExpensesOverAssets')         as gross_expense_ratio,
        median(value) filter (where tag = 'NetExpensesOverAssets')      as net_expense_ratio
    from {{ ref('int_facts_dated') }}
    where class_id is not null
      and tag in ('ExpensesOverAssets', 'NetExpensesOverAssets')
    group by 1, 2
)

select
    *,
    coalesce(net_expense_ratio, gross_expense_ratio)                    as effective_expense_ratio,
    coalesce(net_expense_ratio, gross_expense_ratio)
        between 0 and {{ var('max_expense_ratio') }}                    as is_valid
from ratios
where coalesce(net_expense_ratio, gross_expense_ratio) is not null
