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

fifa_rankings as (
    select *
    from {{ ref('int_historical_match_rankings') }}
),

external_match_features as (
    select *
    from {{ ref('stg_international_match_features') }}
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
        away_form.prior_10_goals_against_per_match as away_prior_10_goals_against_per_match,
        fifa_rankings.home_fifa_ranking_date,
        fifa_rankings.away_fifa_ranking_date,
        fifa_rankings.home_fifa_rank,
        fifa_rankings.away_fifa_rank,
        fifa_rankings.home_fifa_points,
        fifa_rankings.away_fifa_points,
        fifa_rankings.fifa_rank_diff,
        fifa_rankings.fifa_points_diff,
        fifa_rankings.has_complete_fifa_rankings,
        external_match_features.external_home_elo,
        external_match_features.external_away_elo,
        external_match_features.external_elo_diff,
        external_match_features.external_home_avg_overall,
        external_match_features.external_home_max_overall,
        external_match_features.external_home_avg_attack,
        external_match_features.external_home_avg_defense,
        external_match_features.external_home_avg_pace,
        external_match_features.external_home_avg_shooting,
        external_match_features.external_home_avg_passing,
        external_match_features.external_home_star_power,
        external_match_features.external_home_superstar_gap,
        external_match_features.external_home_attacking_star_power,
        external_match_features.external_away_avg_overall,
        external_match_features.external_away_max_overall,
        external_match_features.external_away_avg_attack,
        external_match_features.external_away_avg_defense,
        external_match_features.external_away_avg_pace,
        external_match_features.external_away_avg_shooting,
        external_match_features.external_away_avg_passing,
        external_match_features.external_away_star_power,
        external_match_features.external_away_superstar_gap,
        external_match_features.external_away_attacking_star_power,
        external_match_features.external_overall_diff,
        external_match_features.external_attack_diff,
        external_match_features.external_defense_diff,
        external_match_features.external_star_power_diff,
        external_match_features.external_superstar_gap_diff,
        external_match_features.external_attacking_star_power_diff,
        external_match_features.external_home_form_scored,
        external_match_features.external_home_form_conceded,
        external_match_features.external_home_form_win_rate,
        external_match_features.external_away_form_scored,
        external_match_features.external_away_form_conceded,
        external_match_features.external_away_form_win_rate,
        external_match_features.external_is_neutral,
        external_match_features.external_is_world_cup,
        external_match_features.external_is_continental,
        external_match_features.match_date is not null as has_external_match_features
    from matches
    inner join home_form
        on matches.result_id = home_form.result_id
        and matches.home_team = home_form.team_name
    inner join away_form
        on matches.result_id = away_form.result_id
        and matches.away_team = away_form.team_name
    left join fifa_rankings
        on matches.result_id = fifa_rankings.result_id
    left join external_match_features
        on matches.match_date = external_match_features.match_date
        and matches.home_team = external_match_features.home_team
        and matches.away_team = external_match_features.away_team
        and matches.home_score = external_match_features.home_goals
        and matches.away_score = external_match_features.away_goals
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
