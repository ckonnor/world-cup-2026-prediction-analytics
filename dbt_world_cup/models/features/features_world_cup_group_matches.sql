with fixtures as (
    select *
    from {{ ref('stg_group_fixtures') }}
),

team_strength as (
    select *
    from {{ ref('mart_team_strength') }}
),

squad_strength as (
    select *
    from {{ ref('mart_squad_strength') }}
),

joined as (
    select
        fixtures.match_id,
        fixtures.group_letter,
        fixtures.match_date_utc,
        fixtures.venue,
        fixtures.home_team,
        fixtures.away_team,
        fixtures.home_team_raw,
        fixtures.away_team_raw,
        fixtures.home_team_model_name,
        fixtures.away_team_model_name,
        fixtures.home_team_was_resolved,
        fixtures.away_team_was_resolved,
        home_strength.latest_match_date as home_latest_match_date,
        away_strength.latest_match_date as away_latest_match_date,
        home_strength.historical_matches as home_historical_matches,
        away_strength.historical_matches as away_historical_matches,
        home_strength.last_10_matches as home_last_10_matches,
        away_strength.last_10_matches as away_last_10_matches,
        home_strength.last_10_points_per_match as home_last_10_points_per_match,
        away_strength.last_10_points_per_match as away_last_10_points_per_match,
        home_strength.last_10_goal_diff_per_match as home_last_10_goal_diff_per_match,
        away_strength.last_10_goal_diff_per_match as away_last_10_goal_diff_per_match,
        home_strength.last_10_goals_for_per_match as home_last_10_goals_for_per_match,
        away_strength.last_10_goals_for_per_match as away_last_10_goals_for_per_match,
        home_strength.last_10_goals_against_per_match as home_last_10_goals_against_per_match,
        away_strength.last_10_goals_against_per_match as away_last_10_goals_against_per_match,
        home_strength.days_since_latest_match as home_days_since_latest_match,
        away_strength.days_since_latest_match as away_days_since_latest_match,
        home_strength.team_name is not null as has_home_strength_features,
        away_strength.team_name is not null as has_away_strength_features,
        home_squad.squad_players as home_squad_players,
        away_squad.squad_players as away_squad_players,
        home_squad.squad_status as home_squad_status,
        away_squad.squad_status as away_squad_status,
        home_squad.overall_star_power_z as home_overall_star_power_z,
        away_squad.overall_star_power_z as away_overall_star_power_z,
        home_squad.attacking_star_power_z as home_attacking_star_power_z,
        away_squad.attacking_star_power_z as away_attacking_star_power_z,
        home_squad.defensive_experience_z as home_defensive_experience_z,
        away_squad.defensive_experience_z as away_defensive_experience_z,
        home_squad.total_caps as home_squad_total_caps,
        away_squad.total_caps as away_squad_total_caps,
        home_squad.total_goals as home_squad_total_goals,
        away_squad.total_goals as away_squad_total_goals,
        home_squad.team_name is not null as has_home_squad_features,
        away_squad.team_name is not null as has_away_squad_features
    from fixtures
    left join team_strength as home_strength
        on fixtures.home_team_model_name = home_strength.team_name
    left join team_strength as away_strength
        on fixtures.away_team_model_name = away_strength.team_name
    left join squad_strength as home_squad
        on fixtures.home_team_model_name = home_squad.team_name
    left join squad_strength as away_squad
        on fixtures.away_team_model_name = away_squad.team_name
)

select
    *,
    home_last_10_points_per_match - away_last_10_points_per_match as last_10_points_per_match_diff,
    home_last_10_goal_diff_per_match - away_last_10_goal_diff_per_match as last_10_goal_diff_per_match_diff,
    home_last_10_goals_for_per_match - away_last_10_goals_for_per_match as last_10_goals_for_per_match_diff,
    home_last_10_goals_against_per_match - away_last_10_goals_against_per_match as last_10_goals_against_per_match_diff,
    coalesce(home_overall_star_power_z, 0) - coalesce(away_overall_star_power_z, 0) as overall_star_power_diff,
    coalesce(home_attacking_star_power_z, 0) - coalesce(away_defensive_experience_z, 0) as home_attack_vs_away_defense_diff,
    coalesce(away_attacking_star_power_z, 0) - coalesce(home_defensive_experience_z, 0) as away_attack_vs_home_defense_diff,
    has_home_strength_features and has_away_strength_features as has_complete_strength_features,
    has_home_squad_features and has_away_squad_features as has_complete_squad_features
from joined
