select
    match_id,
    competition_phase,
    group_letter,
    round_name,
    score_multiplier,
    home_team,
    away_team,
    home_team_model_name,
    away_team_model_name,
    match_date_utc,
    venue,
    uses_slot_labels
from {{ ref('int_fixture_slots') }}
