with world_cup_teams as (
    select
        team_model_name as team_name,
        min(team_name) as display_team_name,
        min(group_letter) as group_letter
    from {{ ref('dim_teams') }}
    group by 1
),

international_events as (
    select *
    from {{ ref('int_footystats_team_match_events') }}
),

international_team_rates as (
    select
        team_name,
        count(*) as international_event_matches,
        max(match_date) as latest_event_match_date,
        round(sum(corners_for * source_weight) / nullif(sum(source_weight), 0), 3) as avg_corners_for,
        round(sum(corners_against * source_weight) / nullif(sum(source_weight), 0), 3) as avg_corners_against,
        round(sum(yellow_cards_for * source_weight) / nullif(sum(source_weight), 0), 3) as avg_yellow_cards_for,
        round(sum(yellow_cards_against * source_weight) / nullif(sum(source_weight), 0), 3) as avg_yellow_cards_against,
        round(sum(red_cards_for * source_weight) / nullif(sum(source_weight), 0), 3) as avg_red_cards_for,
        round(sum(red_cards_against * source_weight) / nullif(sum(source_weight), 0), 3) as avg_red_cards_against
    from international_events
    group by 1
),

global_international_defaults as (
    select
        round(sum(corners_for * source_weight) / nullif(sum(source_weight), 0), 3) as avg_corners_for,
        round(sum(corners_against * source_weight) / nullif(sum(source_weight), 0), 3) as avg_corners_against,
        round(sum(yellow_cards_for * source_weight) / nullif(sum(source_weight), 0), 3) as avg_yellow_cards_for,
        round(sum(yellow_cards_against * source_weight) / nullif(sum(source_weight), 0), 3) as avg_yellow_cards_against,
        round(sum(red_cards_for * source_weight) / nullif(sum(source_weight), 0), 3) as avg_red_cards_for,
        round(sum(red_cards_against * source_weight) / nullif(sum(source_weight), 0), 3) as avg_red_cards_against
    from international_events
),

squad_player_discipline as (
    select *
    from {{ ref('int_squad_player_discipline') }}
),

club_discipline_rates as (
    select
        team_name,
        count(*) as squad_players,
        sum(case when has_club_player_stats then 1 else 0 end) as matched_club_players,
        round(sum(club_minutes), 1) as matched_club_minutes,
        round(sum(club_nineties), 3) as matched_club_nineties,
        round(sum(club_yellow_cards), 3) as club_yellow_cards,
        round(sum(club_red_cards), 3) as club_red_cards,
        round(sum(club_fouls_committed), 3) as club_fouls_committed,
        round(sum(club_yellow_cards) / nullif(sum(club_nineties), 0), 4) as club_player_yellow_cards_per_90,
        round(sum(club_red_cards) / nullif(sum(club_nineties), 0), 4) as club_player_red_cards_per_90,
        round(sum(club_fouls_committed) / nullif(sum(club_nineties), 0), 4) as club_player_fouls_committed_per_90,
        round(11 * sum(club_yellow_cards) / nullif(sum(club_nineties), 0), 3) as club_projected_yellow_cards_per_match,
        round(11 * sum(club_red_cards) / nullif(sum(club_nineties), 0), 3) as club_projected_red_cards_per_match,
        round(11 * sum(club_fouls_committed) / nullif(sum(club_nineties), 0), 3) as club_projected_fouls_per_match
    from squad_player_discipline
    group by 1
),

global_club_defaults as (
    select
        round(11 * sum(club_yellow_cards) / nullif(sum(club_nineties), 0), 3) as club_projected_yellow_cards_per_match,
        round(11 * sum(club_red_cards) / nullif(sum(club_nineties), 0), 3) as club_projected_red_cards_per_match,
        round(11 * sum(club_fouls_committed) / nullif(sum(club_nineties), 0), 3) as club_projected_fouls_per_match
    from squad_player_discipline
    where has_club_player_stats
),

joined as (
    select
        world_cup_teams.team_name,
        world_cup_teams.display_team_name,
        world_cup_teams.group_letter,
        coalesce(international_team_rates.international_event_matches, 0) as international_event_matches,
        international_team_rates.latest_event_match_date,
        coalesce(international_team_rates.avg_corners_for, global_international_defaults.avg_corners_for) as avg_corners_for,
        coalesce(international_team_rates.avg_corners_against, global_international_defaults.avg_corners_against) as avg_corners_against,
        coalesce(international_team_rates.avg_yellow_cards_for, global_international_defaults.avg_yellow_cards_for) as avg_yellow_cards_for,
        coalesce(international_team_rates.avg_yellow_cards_against, global_international_defaults.avg_yellow_cards_against) as avg_yellow_cards_against,
        coalesce(international_team_rates.avg_red_cards_for, global_international_defaults.avg_red_cards_for) as avg_red_cards_for,
        coalesce(international_team_rates.avg_red_cards_against, global_international_defaults.avg_red_cards_against) as avg_red_cards_against,
        coalesce(club_discipline_rates.squad_players, 0) as squad_players,
        coalesce(club_discipline_rates.matched_club_players, 0) as matched_club_players,
        coalesce(club_discipline_rates.matched_club_minutes, 0) as matched_club_minutes,
        coalesce(club_discipline_rates.matched_club_nineties, 0) as matched_club_nineties,
        club_discipline_rates.club_player_yellow_cards_per_90,
        club_discipline_rates.club_player_red_cards_per_90,
        club_discipline_rates.club_player_fouls_committed_per_90,
        coalesce(
            club_discipline_rates.club_projected_yellow_cards_per_match,
            global_club_defaults.club_projected_yellow_cards_per_match
        ) as club_projected_yellow_cards_per_match,
        coalesce(
            club_discipline_rates.club_projected_red_cards_per_match,
            global_club_defaults.club_projected_red_cards_per_match
        ) as club_projected_red_cards_per_match,
        coalesce(
            club_discipline_rates.club_projected_fouls_per_match,
            global_club_defaults.club_projected_fouls_per_match
        ) as club_projected_fouls_per_match
    from world_cup_teams
    cross join global_international_defaults
    cross join global_club_defaults
    left join international_team_rates
        on world_cup_teams.team_name = international_team_rates.team_name
    left join club_discipline_rates
        on world_cup_teams.team_name = club_discipline_rates.team_name
)

select
    *,
    round(matched_club_players / nullif(squad_players, 0), 3) as club_player_match_coverage,
    round(
        case
            when matched_club_players >= 3 then
                0.60 * club_projected_yellow_cards_per_match + 0.40 * avg_yellow_cards_for
            else avg_yellow_cards_for
        end,
        3
    ) as blended_yellow_cards_for,
    round(
        case
            when matched_club_players >= 3 then
                0.45 * club_projected_red_cards_per_match + 0.55 * avg_red_cards_for
            else avg_red_cards_for
        end,
        3
    ) as blended_red_cards_for
from joined
