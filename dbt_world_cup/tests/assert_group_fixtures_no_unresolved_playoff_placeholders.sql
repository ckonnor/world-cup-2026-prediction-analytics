select *
from {{ ref('stg_group_fixtures') }}
where home_team ilike '%playoff%'
    or away_team ilike '%playoff%'
