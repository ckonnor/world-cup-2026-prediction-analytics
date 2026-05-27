select
    count(*) as group_match_count
from {{ ref('stg_group_fixtures') }}
having count(*) != 72
