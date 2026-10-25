-- The SEC's yearly fund lists, restricted to well-formed identifiers.

select
    list_year,
    series_id,
    series_name,
    class_id,
    class_name,
    ticker,
    entity_name,
    entity_org_type
from {{ source('sec', 'series_class') }}
where regexp_full_match(class_id, 'C[0-9]{9}')
  and regexp_full_match(series_id, 'S[0-9]{9}')
