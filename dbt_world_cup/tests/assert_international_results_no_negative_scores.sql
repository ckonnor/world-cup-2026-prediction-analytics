select
    result_id,
    home_score,
    away_score
from {{ ref('stg_international_results') }}
where home_score < 0
    or away_score < 0
