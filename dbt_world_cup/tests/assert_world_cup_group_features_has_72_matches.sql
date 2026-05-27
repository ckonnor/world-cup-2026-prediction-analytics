select
    count(*) as group_match_count
from {{ ref('features_world_cup_group_matches') }}
having count(*) != 72
