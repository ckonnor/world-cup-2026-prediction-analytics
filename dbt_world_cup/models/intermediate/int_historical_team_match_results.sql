with results as (
    select *
    from {{ ref('stg_international_results') }}
),

home_rows as (
    select
        result_id,
        match_date,
        tournament,
        city,
        country,
        neutral,
        home_team as team_name,
        away_team as opponent_name,
        true as is_home_team,
        home_score as goals_for,
        away_score as goals_against
    from results
),

away_rows as (
    select
        result_id,
        match_date,
        tournament,
        city,
        country,
        neutral,
        away_team as team_name,
        home_team as opponent_name,
        false as is_home_team,
        away_score as goals_for,
        home_score as goals_against
    from results
)

select
    result_id,
    match_date,
    tournament,
    city,
    country,
    neutral,
    team_name,
    opponent_name,
    is_home_team,
    goals_for,
    goals_against,
    goals_for - goals_against as goal_difference,
    case
        when goals_for > goals_against then 'win'
        when goals_for = goals_against then 'draw'
        else 'loss'
    end as match_result,
    case
        when goals_for > goals_against then 3
        when goals_for = goals_against then 1
        else 0
    end as points
from home_rows

union all

select
    result_id,
    match_date,
    tournament,
    city,
    country,
    neutral,
    team_name,
    opponent_name,
    is_home_team,
    goals_for,
    goals_against,
    goals_for - goals_against as goal_difference,
    case
        when goals_for > goals_against then 'win'
        when goals_for = goals_against then 'draw'
        else 'loss'
    end as match_result,
    case
        when goals_for > goals_against then 3
        when goals_for = goals_against then 1
        else 0
    end as points
from away_rows
