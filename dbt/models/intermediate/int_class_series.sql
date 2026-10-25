-- Which fund each share class belongs to.
--
-- Facts are the primary source: rr facts always carry the series, oef facts
-- often only the class. The SEC's yearly lists fill in classes that never
-- appear next to a series in the facts.
--
-- 711 classes appear under more than one series. Each takes the series it is
-- filed under most often, ties broken by the lower series ID, so every build
-- assigns the same fund: mode() would pick an arbitrary winner on a tie.

with fact_counts as (
    select class_id, series_id, count(*) as appearances
    from {{ ref('stg_facts') }}
    where class_id is not null and series_id is not null
    group by 1, 2
),

from_facts as (
    select
        class_id,
        series_id,
        count(*) over (partition by class_id)   as series_seen,
        row_number() over (
            partition by class_id
            order by appearances desc, series_id
        )                                       as preference
    from fact_counts
),

from_lists as (
    select
        class_id,
        series_id,
        row_number() over (
            partition by class_id
            order by list_year desc, series_id
        )                                       as preference
    from {{ ref('stg_series_class') }}
),

classes as (
    select distinct class_id from {{ ref('stg_facts') }} where class_id is not null
)

select
    c.class_id,
    coalesce(f.series_id, l.series_id)                      as series_id,
    case when f.series_id is not null then 'facts' else 'series list' end
                                                            as series_source,
    coalesce(f.series_seen, 1)                              as series_seen
from classes c
left join from_facts f on f.class_id = c.class_id and f.preference = 1
left join from_lists l on l.class_id = c.class_id and l.preference = 1
where coalesce(f.series_id, l.series_id) is not null
