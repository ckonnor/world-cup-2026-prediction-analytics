select
    result_id,
    match_date,
    home_team,
    away_team
from {{ ref('features_historical_match_training') }}
where home_prior_10_matches < 5
    or away_prior_10_matches < 5
