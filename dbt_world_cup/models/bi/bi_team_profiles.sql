with teams as (
    select *
    from {{ ref('dim_teams') }}
),

team_strength as (
    select *
    from {{ ref('mart_team_strength') }}
),

fifa_rankings as (
    select *
    from {{ ref('mart_latest_fifa_rankings') }}
),

squad_strength as (
    select *
    from {{ ref('mart_squad_strength') }}
),

event_profile as (
    select *
    from {{ ref('mart_team_event_profile') }}
),

external_player_strength as (
    select *
    from {{ ref('mart_external_player_strength') }}
)

select
    teams.team_id,
    teams.team_name,
    teams.team_model_name,
    teams.group_letter,
    team_strength.historical_matches,
    team_strength.latest_match_date,
    team_strength.days_since_latest_match,
    team_strength.last_10_matches,
    team_strength.last_10_points_per_match,
    team_strength.last_10_goal_diff_per_match,
    team_strength.last_10_goals_for_per_match,
    team_strength.last_10_goals_against_per_match,
    fifa_rankings.ranking_date as fifa_ranking_date,
    fifa_rankings.fifa_rank,
    fifa_rankings.fifa_points,
    fifa_rankings.previous_fifa_rank,
    fifa_rankings.previous_fifa_points,
    fifa_rankings.confederation,
    squad_strength.squad_status,
    squad_strength.squad_players,
    squad_strength.average_age,
    squad_strength.total_caps,
    squad_strength.total_goals,
    squad_strength.attacking_star_power_z,
    squad_strength.defensive_experience_z,
    squad_strength.experience_score_z,
    squad_strength.overall_star_power_z,
    event_profile.international_event_matches,
    event_profile.latest_event_match_date,
    event_profile.avg_corners_for,
    event_profile.avg_corners_against,
    event_profile.blended_yellow_cards_for,
    event_profile.blended_red_cards_for,
    event_profile.matched_club_players,
    event_profile.club_player_match_coverage,
    external_player_strength.avg_overall as external_avg_overall,
    external_player_strength.max_overall as external_max_overall,
    external_player_strength.avg_attack_overall as external_avg_attack_overall,
    external_player_strength.avg_defense_overall as external_avg_defense_overall,
    external_player_strength.player_star_power_index,
    external_player_strength.superstar_gap,
    external_player_strength.attacking_star_power_index,
    team_strength.team_name is not null as has_form_profile,
    fifa_rankings.team_name is not null as has_fifa_profile,
    squad_strength.team_name is not null as has_squad_profile,
    event_profile.team_name is not null as has_event_profile,
    external_player_strength.team_name is not null as has_external_player_profile,
    round(
        (
            case when team_strength.team_name is not null then 1 else 0 end
            + case when fifa_rankings.team_name is not null then 1 else 0 end
            + case when squad_strength.team_name is not null then 1 else 0 end
            + case when event_profile.team_name is not null then 1 else 0 end
            + case when external_player_strength.team_name is not null then 1 else 0 end
        ) / 5.0,
        2
    ) as profile_completeness_score
from teams
left join team_strength
    on teams.team_model_name = team_strength.team_name
left join fifa_rankings
    on teams.team_model_name = fifa_rankings.team_name
left join squad_strength
    on teams.team_model_name = squad_strength.team_name
left join event_profile
    on teams.team_model_name = event_profile.team_name
left join external_player_strength
    on teams.team_model_name = external_player_strength.team_name
