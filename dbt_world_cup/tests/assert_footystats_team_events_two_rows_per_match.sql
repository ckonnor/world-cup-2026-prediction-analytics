select
    source_match_id,
    count(*) as team_rows
from {{ ref('int_footystats_team_match_events') }}
group by 1
having count(*) != 2
