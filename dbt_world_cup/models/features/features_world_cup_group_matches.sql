with fixtures as (
    select *
    from {{ ref('stg_group_fixtures') }}
),

team_strength as (
    select *
    from {{ ref('mart_team_strength') }}
),

joined as (
    select
        fixtures.match_id,
        fixtures.group_letter,
        fixtures.match_date_utc,
        fixtures.venue,
        fixtures.home_team,
        fixtures.away_team,
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
        away_strength.team_name is not null as has_away_strength_features
    from fixtures
    left join team_strength as home_strength
        on fixtures.home_team = home_strength.team_name
    left join team_strength as away_strength
        on fixtures.away_team = away_strength.team_name
)

select
    *,
    home_last_10_points_per_match - away_last_10_points_per_match as last_10_points_per_match_diff,
    home_last_10_goal_diff_per_match - away_last_10_goal_diff_per_match as last_10_goal_diff_per_match_diff,
    home_last_10_goals_for_per_match - away_last_10_goals_for_per_match as last_10_goals_for_per_match_diff,
    home_last_10_goals_against_per_match - away_last_10_goals_against_per_match as last_10_goals_against_per_match_diff,
    has_home_strength_features and has_away_strength_features as has_complete_strength_features
from joined
