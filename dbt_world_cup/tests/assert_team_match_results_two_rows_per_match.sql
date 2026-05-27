select
    result_id,
    count(*) as team_rows
from {{ ref('int_historical_team_match_results') }}
group by 1
having count(*) != 2
