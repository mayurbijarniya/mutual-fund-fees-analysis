-- One row per share class: its fund, name, ticker, typical fee and whether it
-- is still filing.

with activity as (
    select
        class_id,
        min(quarter)                    as first_quarter,
        max(quarter)                    as last_quarter,
        count(distinct accession_number) as filings
    from {{ ref('stg_facts') }}
    where class_id is not null
    group by 1
),

fees as (
    select
        class_id,
        median(effective_expense_ratio) as median_expense_ratio,
        count(*)                        as fee_filings
    from {{ ref('int_expense_ratios') }}
    where is_valid
    group by 1
),

-- Name and ticker from the most recent list that has one, ties broken by value
-- so every build picks the same row.
class_names as (
    select class_id, class_name,
           row_number() over (partition by class_id order by list_year desc, class_name)
               as preference
    from {{ ref('stg_series_class') }}
),

tickers as (
    select class_id, ticker,
           row_number() over (partition by class_id order by list_year desc, ticker)
               as preference
    from {{ ref('stg_series_class') }}
    where ticker is not null
),

names as (
    select n.class_id, n.class_name, t.ticker
    from class_names n
    left join tickers t on t.class_id = n.class_id and t.preference = 1
    where n.preference = 1
)

select
    m.class_id,
    m.series_id,
    n.class_name,
    n.ticker,
    a.first_quarter,
    a.last_quarter,
    a.filings,
    f.median_expense_ratio,
    f.fee_filings,
    case
        when a.last_quarter >= '{{ var("active_since_quarter") }}' then 'active'
        else 'stopped filing'
    end                                 as status
from {{ ref('int_class_series') }} m
join activity a using (class_id)
left join fees f using (class_id)
left join names n using (class_id)
