with predictions as (
    select
        match_id,
        competition_phase,
        group_letter,
        round_name,
        score_multiplier,
        home_team,
        away_team,
        case
            when competition_phase = 'knockout' then 1
            else 1
        end as predicted_home_goals,
        case
            when competition_phase = 'knockout' then 0
            else 1
        end as predicted_away_goals,
        5 as predicted_home_corners,
        4 as predicted_away_corners,
        2 as predicted_home_yellow_cards,
        2 as predicted_away_yellow_cards,
        0 as predicted_home_red_cards,
        0 as predicted_away_red_cards
    from {{ ref('fct_fixture_schedule') }}
)

select
    *,
    case
        when predicted_home_goals > predicted_away_goals then home_team
        when predicted_away_goals > predicted_home_goals then away_team
        else 'Draw'
    end as predicted_result
from predictions
