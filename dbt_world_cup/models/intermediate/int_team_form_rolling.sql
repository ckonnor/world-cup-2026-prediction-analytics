select
    result_id,
    match_date,
    team_name,
    opponent_name,
    tournament,
    is_home_team,
    goals_for,
    goals_against,
    goal_difference,
    match_result,
    points,
    count(*) over (
        partition by team_name
        order by match_date, result_id
        rows between 10 preceding and 1 preceding
    ) as prior_10_matches,
    avg(points) over (
        partition by team_name
        order by match_date, result_id
        rows between 10 preceding and 1 preceding
    ) as prior_10_points_per_match,
    avg(goal_difference) over (
        partition by team_name
        order by match_date, result_id
        rows between 10 preceding and 1 preceding
    ) as prior_10_goal_diff_per_match,
    avg(goals_for) over (
        partition by team_name
        order by match_date, result_id
        rows between 10 preceding and 1 preceding
    ) as prior_10_goals_for_per_match,
    avg(goals_against) over (
        partition by team_name
        order by match_date, result_id
        rows between 10 preceding and 1 preceding
    ) as prior_10_goals_against_per_match
from {{ ref('int_historical_team_match_results') }}
