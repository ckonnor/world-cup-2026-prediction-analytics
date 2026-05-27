with matches as (
    select *
    from {{ ref('stg_international_results') }}
),

home_form as (
    select *
    from {{ ref('int_team_form_rolling') }}
    where is_home_team
),

away_form as (
    select *
    from {{ ref('int_team_form_rolling') }}
    where not is_home_team
),

joined as (
    select
        matches.result_id,
        matches.match_date,
        matches.tournament,
        matches.country,
        matches.neutral,
        matches.home_team,
        matches.away_team,
        matches.home_score,
        matches.away_score,
        matches.home_score - matches.away_score as goal_difference,
        case
            when matches.home_score > matches.away_score then 'home'
            when matches.home_score < matches.away_score then 'away'
            else 'draw'
        end as match_outcome,
        home_form.prior_10_matches as home_prior_10_matches,
        away_form.prior_10_matches as away_prior_10_matches,
        home_form.prior_10_points_per_match as home_prior_10_points_per_match,
        away_form.prior_10_points_per_match as away_prior_10_points_per_match,
        home_form.prior_10_goal_diff_per_match as home_prior_10_goal_diff_per_match,
        away_form.prior_10_goal_diff_per_match as away_prior_10_goal_diff_per_match,
        home_form.prior_10_goals_for_per_match as home_prior_10_goals_for_per_match,
        away_form.prior_10_goals_for_per_match as away_prior_10_goals_for_per_match,
        home_form.prior_10_goals_against_per_match as home_prior_10_goals_against_per_match,
        away_form.prior_10_goals_against_per_match as away_prior_10_goals_against_per_match
    from matches
    inner join home_form
        on matches.result_id = home_form.result_id
        and matches.home_team = home_form.team_name
    inner join away_form
        on matches.result_id = away_form.result_id
        and matches.away_team = away_form.team_name
)

select
    *,
    home_prior_10_points_per_match - away_prior_10_points_per_match as prior_10_points_per_match_diff,
    home_prior_10_goal_diff_per_match - away_prior_10_goal_diff_per_match as prior_10_goal_diff_per_match_diff,
    home_prior_10_goals_for_per_match - away_prior_10_goals_for_per_match as prior_10_goals_for_per_match_diff,
    home_prior_10_goals_against_per_match - away_prior_10_goals_against_per_match as prior_10_goals_against_per_match_diff
from joined
where home_prior_10_matches >= 5
    and away_prior_10_matches >= 5
