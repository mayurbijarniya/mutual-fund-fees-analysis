-- One typed row per numeric fact. The share class lives in its own column in
-- the rr taxonomy and inside the `otherdims` string ("Class=C000038531;") in oef.

select
    adsh                                                    as accession_number,
    tag,
    split_part(version, '/', 1)                             as taxonomy,
    try_strptime(ddate, '%Y%m%d')::date                     as period_end,
    nullif(series, '')                                      as series_id,
    coalesce(
        nullif(class, ''),
        nullif(regexp_extract(otherdims, 'Class=(C[0-9]{9})', 1), '')
    )                                                       as class_id,
    nullif(measure, '')                                     as measure,
    try_cast(value as double)                               as value,
    quarter
from {{ source('sec', 'facts') }}
