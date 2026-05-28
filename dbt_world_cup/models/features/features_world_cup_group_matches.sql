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

team_event_profile as (
    select *
    from {{ ref('mart_team_event_profile') }}
),

fifa_rankings as (
    select *
    from {{ ref('mart_latest_fifa_rankings') }}
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
        away_squad.team_name is not null as has_away_squad_features,
        home_events.international_event_matches as home_international_event_matches,
        away_events.international_event_matches as away_international_event_matches,
        home_events.matched_club_players as home_matched_club_players,
        away_events.matched_club_players as away_matched_club_players,
        home_events.club_player_match_coverage as home_club_player_match_coverage,
        away_events.club_player_match_coverage as away_club_player_match_coverage,
        home_events.avg_corners_for as home_avg_corners_for,
        away_events.avg_corners_for as away_avg_corners_for,
        home_events.avg_corners_against as home_avg_corners_against,
        away_events.avg_corners_against as away_avg_corners_against,
        home_events.blended_yellow_cards_for as home_blended_yellow_cards_for,
        away_events.blended_yellow_cards_for as away_blended_yellow_cards_for,
        home_events.avg_yellow_cards_against as home_avg_yellow_cards_against,
        away_events.avg_yellow_cards_against as away_avg_yellow_cards_against,
        home_events.blended_red_cards_for as home_blended_red_cards_for,
        away_events.blended_red_cards_for as away_blended_red_cards_for,
        home_events.avg_red_cards_against as home_avg_red_cards_against,
        away_events.avg_red_cards_against as away_avg_red_cards_against,
        home_events.team_name is not null as has_home_event_features,
        away_events.team_name is not null as has_away_event_features,
        home_fifa.ranking_date as home_fifa_ranking_date,
        away_fifa.ranking_date as away_fifa_ranking_date,
        home_fifa.fifa_rank as home_fifa_rank,
        away_fifa.fifa_rank as away_fifa_rank,
        home_fifa.fifa_points as home_fifa_points,
        away_fifa.fifa_points as away_fifa_points,
        home_fifa.team_name is not null as has_home_fifa_ranking,
        away_fifa.team_name is not null as has_away_fifa_ranking
    from fixtures
    left join team_strength as home_strength
        on fixtures.home_team_model_name = home_strength.team_name
    left join team_strength as away_strength
        on fixtures.away_team_model_name = away_strength.team_name
    left join squad_strength as home_squad
        on fixtures.home_team_model_name = home_squad.team_name
    left join squad_strength as away_squad
        on fixtures.away_team_model_name = away_squad.team_name
    left join team_event_profile as home_events
        on fixtures.home_team_model_name = home_events.team_name
    left join team_event_profile as away_events
        on fixtures.away_team_model_name = away_events.team_name
    left join fifa_rankings as home_fifa
        on fixtures.home_team_model_name = home_fifa.team_name
    left join fifa_rankings as away_fifa
        on fixtures.away_team_model_name = away_fifa.team_name
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
    has_home_squad_features and has_away_squad_features as has_complete_squad_features,
    has_home_event_features and has_away_event_features as has_complete_event_features,
    has_home_fifa_ranking and has_away_fifa_ranking as has_complete_fifa_rankings,
    home_fifa_rank - away_fifa_rank as fifa_rank_diff,
    home_fifa_points - away_fifa_points as fifa_points_diff,
    round(
        (
            home_avg_corners_for
            + away_avg_corners_for
            + home_avg_corners_against
            + away_avg_corners_against
        ) / 2,
        3
    ) as expected_total_corners,
    round(
        (
            home_blended_yellow_cards_for
            + away_blended_yellow_cards_for
            + home_avg_yellow_cards_against
            + away_avg_yellow_cards_against
        ) / 2,
        3
    ) as expected_total_yellow_cards,
    round(
        (
            home_blended_red_cards_for
            + away_blended_red_cards_for
            + home_avg_red_cards_against
            + away_avg_red_cards_against
        ) / 2,
        3
    ) as expected_total_red_cards
from joined
