-- One row per fund (SEC series). A fund is active while any of its share
-- classes is still filing.

-- Names come from the most recent list; a series can appear on several rows of
-- one year's list, so ties are broken by name to keep every build identical.
with ranked as (
    select
        series_id,
        series_name,
        entity_name,
        row_number() over (
            partition by series_id
            order by list_year desc, series_name, entity_name
        ) as preference
    from {{ ref('stg_series_class') }}
),

names as (
    select series_id, series_name as fund_name, entity_name as fund_family
    from ranked
    where preference = 1
)

select
    c.series_id,
    n.fund_name,
    n.fund_family,
    count(*)                                                    as share_classes,
    min(c.first_quarter)                                        as first_quarter,
    max(c.last_quarter)                                         as last_quarter,
    median(c.median_expense_ratio)                              as median_expense_ratio,
    case when bool_or(c.status = 'active') then 'active' else 'stopped filing' end
                                                                as status
from {{ ref('dim_share_class') }} c
left join names n using (series_id)
group by c.series_id, n.fund_name, n.fund_family
