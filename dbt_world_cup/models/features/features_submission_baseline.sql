with predictions as (
    select
        match_id,
        competition_phase,
        group_letter,
        round_name,
        score_multiplier,
        home_team,
        away_team,
        1 as predicted_home_goals,
        case when competition_phase = 'knockout' then 0 else 1 end as predicted_away_goals,
        9 as corners,
        4 as yellow_cards,
        0 as red_cards
    from {{ ref('fct_fixture_schedule') }}
)

select
    *,
    case
        when competition_phase = 'knockout' then null
        when predicted_home_goals > predicted_away_goals then home_team
        when predicted_away_goals > predicted_home_goals then away_team
        else 'draw'
    end as winning_team,
    case when competition_phase = 'knockout' then home_team end as predicted_home_team,
    case when competition_phase = 'knockout' then away_team end as predicted_away_team,
    case when competition_phase = 'knockout' then 'home' end as match_winner,
    case when competition_phase = 'knockout' then false end as penalties
from predictions
