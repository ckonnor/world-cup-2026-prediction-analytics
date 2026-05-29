with squad_players as (
    select *
    from {{ ref('stg_world_cup_squads') }}
),

player_discipline as (
    select *
    from {{ ref('int_squad_player_discipline') }}
),

teams as (
    select
        team_name as display_team_name,
        team_model_name,
        group_letter
    from {{ ref('dim_teams') }}
),

enriched as (
    select
        coalesce(teams.display_team_name, squad_players.team_name) as team_name,
        coalesce(teams.team_model_name, squad_players.team_name) as team_model_name,
        teams.group_letter,
        player_discipline.country_code,
        squad_players.squad_status,
        squad_players.source_player_count,
        squad_players.shirt_number,
        squad_players.position,
        squad_players.player_name,
        squad_players.player_name_key,
        squad_players.is_captain,
        squad_players.age,
        squad_players.caps,
        squad_players.goals as international_goals,
        squad_players.club as squad_club,
        coalesce(player_discipline.club_names, squad_players.club) as matched_clubs,
        player_discipline.competitions,
        coalesce(player_discipline.club_matches_played, 0) as club_matches_played,
        coalesce(player_discipline.club_starts, 0) as club_starts,
        coalesce(player_discipline.club_minutes, 0) as club_minutes,
        coalesce(player_discipline.club_nineties, 0) as club_nineties,
        coalesce(player_discipline.club_goals, 0) as club_goals,
        coalesce(player_discipline.club_assists, 0) as club_assists,
        coalesce(player_discipline.club_yellow_cards, 0) as club_yellow_cards,
        coalesce(player_discipline.club_red_cards, 0) as club_red_cards,
        coalesce(player_discipline.club_fouls_committed, 0) as club_fouls_committed,
        coalesce(player_discipline.club_crosses, 0) as club_crosses,
        coalesce(player_discipline.club_tackles_won, 0) as club_tackles_won,
        coalesce(player_discipline.club_interceptions, 0) as club_interceptions,
        coalesce(player_discipline.has_club_player_stats, false) as has_club_player_stats
    from squad_players
    left join player_discipline
        on squad_players.team_name = player_discipline.team_name
        and squad_players.player_name_key = player_discipline.player_name_key
    left join teams
        on squad_players.team_name = teams.team_model_name
),

raw_scores as (
    select
        *,
        (
            0.34 * ln(1 + caps)
            + 0.16 * ln(1 + international_goals)
            + 0.19 * ln(1 + club_minutes / 90.0)
            + 0.15 * ln(1 + club_goals + club_assists)
            + 0.08 * ln(1 + club_starts)
            + 0.05 * ln(1 + club_tackles_won + club_interceptions)
            + case when is_captain then 0.15 else 0 end
        ) as player_power_raw,
        case
            when club_nineties > 0 then (club_goals + club_assists) / club_nineties
        end as club_goal_contribution_per_90,
        case
            when club_nineties > 0 then club_yellow_cards / club_nineties
        end as club_yellow_cards_per_90,
        case
            when club_nineties > 0 then club_fouls_committed / club_nineties
        end as club_fouls_committed_per_90
    from enriched
),

scored as (
    select
        *,
        case
            when stddev_samp(player_power_raw) over () = 0 then 0
            else (player_power_raw - avg(player_power_raw) over ())
                / stddev_samp(player_power_raw) over ()
        end as player_power_z
    from raw_scores
),

ranked as (
    select
        *,
        row_number() over (
            partition by team_name
            order by player_power_z desc, caps desc, international_goals desc, player_name
        ) as team_player_power_rank
    from scored
)

select
    team_name,
    team_model_name,
    group_letter,
    country_code,
    squad_status,
    source_player_count,
    team_player_power_rank,
    shirt_number,
    position,
    player_name,
    is_captain,
    age,
    caps,
    international_goals,
    squad_club,
    matched_clubs,
    competitions,
    club_matches_played,
    club_starts,
    round(club_minutes, 1) as club_minutes,
    club_goals,
    club_assists,
    club_yellow_cards,
    club_red_cards,
    club_fouls_committed,
    club_crosses,
    club_tackles_won,
    club_interceptions,
    has_club_player_stats,
    round(club_goal_contribution_per_90, 3) as club_goal_contribution_per_90,
    round(club_yellow_cards_per_90, 3) as club_yellow_cards_per_90,
    round(club_fouls_committed_per_90, 3) as club_fouls_committed_per_90,
    round(player_power_raw, 3) as player_power_raw,
    round(player_power_z, 3) as player_power_z,
    round(least(100, greatest(0, 50 + 15 * player_power_z)), 1)
        as player_star_power_index
from ranked
