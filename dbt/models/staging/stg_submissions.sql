select
    adsh                                    as accession_number,
    cik,
    name                                    as filer_name,
    form,
    try_strptime(filed, '%Y%m%d')::date     as filed_date,
    quarter
from {{ source('sec', 'submissions') }}
