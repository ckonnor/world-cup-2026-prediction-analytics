with squad_players as (
    select *
    from {{ ref('stg_world_cup_squads') }}
),

team_codes as (
    select *
    from {{ ref('team_country_codes') }}
),

club_player_stats as (
    select
        player_name_key,
        nation_code,
        min(player_name) as club_player_name,
        string_agg(distinct club_name, '; ') as club_names,
        string_agg(distinct competition, '; ') as competitions,
        max(age) as club_age,
        sum(matches_played) as matches_played,
        sum(starts) as starts,
        sum(minutes) as minutes,
        sum(nineties) as nineties,
        sum(goals) as goals,
        sum(assists) as assists,
        sum(yellow_cards) as yellow_cards,
        sum(red_cards) as red_cards,
        sum(second_yellow_cards) as second_yellow_cards,
        sum(fouls_committed) as fouls_committed,
        sum(fouls_drawn) as fouls_drawn,
        sum(crosses) as crosses,
        sum(tackles_won) as tackles_won,
        sum(interceptions) as interceptions
    from {{ ref('stg_club_player_stats') }}
    where player_name_key is not null
        and nation_code is not null
    group by 1, 2
)

select
    squad_players.team_name,
    team_codes.country_code,
    squad_players.player_name,
    squad_players.player_name_key,
    squad_players.position,
    squad_players.age as squad_age,
    squad_players.caps,
    squad_players.goals as international_goals,
    club_player_stats.club_player_name,
    club_player_stats.club_names,
    club_player_stats.competitions,
    club_player_stats.club_age,
    coalesce(club_player_stats.matches_played, 0) as club_matches_played,
    coalesce(club_player_stats.starts, 0) as club_starts,
    coalesce(club_player_stats.minutes, 0) as club_minutes,
    coalesce(club_player_stats.nineties, 0) as club_nineties,
    coalesce(club_player_stats.goals, 0) as club_goals,
    coalesce(club_player_stats.assists, 0) as club_assists,
    coalesce(club_player_stats.yellow_cards, 0) as club_yellow_cards,
    coalesce(club_player_stats.red_cards, 0) as club_red_cards,
    coalesce(club_player_stats.second_yellow_cards, 0) as club_second_yellow_cards,
    coalesce(club_player_stats.fouls_committed, 0) as club_fouls_committed,
    coalesce(club_player_stats.fouls_drawn, 0) as club_fouls_drawn,
    coalesce(club_player_stats.crosses, 0) as club_crosses,
    coalesce(club_player_stats.tackles_won, 0) as club_tackles_won,
    coalesce(club_player_stats.interceptions, 0) as club_interceptions,
    club_player_stats.player_name_key is not null as has_club_player_stats,
    case
        when club_player_stats.nineties > 0
            then club_player_stats.yellow_cards / club_player_stats.nineties
    end as club_yellow_cards_per_90,
    case
        when club_player_stats.nineties > 0
            then club_player_stats.red_cards / club_player_stats.nineties
    end as club_red_cards_per_90,
    case
        when club_player_stats.nineties > 0
            then club_player_stats.fouls_committed / club_player_stats.nineties
    end as club_fouls_committed_per_90
from squad_players
left join team_codes
    on squad_players.team_name = team_codes.team_name
left join club_player_stats
    on squad_players.player_name_key = club_player_stats.player_name_key
    and team_codes.country_code = club_player_stats.nation_code
