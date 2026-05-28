select
    count(*) as team_count
from {{ ref('mart_team_event_profile') }}
having count(*) != 48
