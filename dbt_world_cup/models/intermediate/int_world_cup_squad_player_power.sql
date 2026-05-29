with squad_players as (
    select *
    from {{ ref('stg_world_cup_squads') }}
),

teams as (
    select
        team_name as display_team_name,
        team_model_name,
        group_letter
    from {{ ref('dim_teams') }}
),

transfermarkt_player_form as (
    select
        *,
        row_number() over (
            partition by citizenship_team_name, player_name_key
            order by
                player_star_power_index desc,
                market_value_in_eur desc,
                top_league_minutes desc,
                player_id
        ) as player_match_rank
    from {{ ref('int_transfermarkt_top_league_player_form') }}
),

matched_players as (
    select
        coalesce(teams.display_team_name, squad_players.team_name) as team_name,
        coalesce(teams.team_model_name, squad_players.team_name) as team_model_name,
        teams.group_letter,
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
        transfermarkt_player_form.player_id as transfermarkt_player_id,
        transfermarkt_player_form.current_club_name as transfermarkt_club,
        transfermarkt_player_form.current_top_league_name,
        transfermarkt_player_form.current_top_league_rank,
        transfermarkt_player_form.current_top_league_rating,
        transfermarkt_player_form.market_value_in_eur,
        transfermarkt_player_form.highest_market_value_in_eur,
        transfermarkt_player_form.transfermarkt_international_caps,
        transfermarkt_player_form.transfermarkt_international_goals,
        transfermarkt_player_form.top_league_appearances,
        transfermarkt_player_form.top_leagues_played,
        transfermarkt_player_form.best_league_rank,
        transfermarkt_player_form.best_league_rating,
        transfermarkt_player_form.top_league_names,
        transfermarkt_player_form.top_league_minutes,
        transfermarkt_player_form.top_league_nineties,
        transfermarkt_player_form.league_weighted_nineties,
        transfermarkt_player_form.top_league_goals,
        transfermarkt_player_form.top_league_assists,
        transfermarkt_player_form.top_league_yellow_cards,
        transfermarkt_player_form.top_league_red_cards,
        transfermarkt_player_form.league_weighted_goals_per90,
        transfermarkt_player_form.league_weighted_assists_per90,
        transfermarkt_player_form.league_weighted_goal_contribution_per90,
        transfermarkt_player_form.sample_reliability,
        transfermarkt_player_form.reliable_goal_contribution_per90,
        transfermarkt_player_form.international_goal_rate_reliable,
        transfermarkt_player_form.top_league_star_power_raw,
        coalesce(transfermarkt_player_form.player_star_power_index, 0)
            as player_star_power_index,
        transfermarkt_player_form.player_id is not null as has_transfermarkt_match,
        transfermarkt_player_form.top_league_appearances > 0 as has_top_league_form
    from squad_players
    left join teams
        on squad_players.team_name = teams.team_model_name
    left join transfermarkt_player_form
        on squad_players.player_name_key = transfermarkt_player_form.player_name_key
        and squad_players.team_name = transfermarkt_player_form.citizenship_team_name
        and transfermarkt_player_form.player_match_rank = 1
),

ranked as (
    select
        *,
        row_number() over (
            partition by team_name
            order by
                player_star_power_index desc,
                top_league_minutes desc nulls last,
                caps desc,
                international_goals desc,
                player_name
        ) as team_player_power_rank
    from matched_players
)

select
    team_name,
    team_model_name,
    group_letter,
    squad_status,
    source_player_count,
    team_player_power_rank,
    shirt_number,
    position,
    player_name,
    player_name_key,
    is_captain,
    age,
    caps,
    international_goals,
    squad_club,
    transfermarkt_player_id,
    transfermarkt_club,
    current_top_league_name,
    current_top_league_rank,
    current_top_league_rating,
    market_value_in_eur,
    highest_market_value_in_eur,
    transfermarkt_international_caps,
    transfermarkt_international_goals,
    top_league_appearances,
    top_leagues_played,
    best_league_rank,
    best_league_rating,
    top_league_names,
    top_league_minutes,
    top_league_nineties,
    league_weighted_nineties,
    top_league_goals,
    top_league_assists,
    top_league_yellow_cards,
    top_league_red_cards,
    league_weighted_goals_per90,
    league_weighted_assists_per90,
    league_weighted_goal_contribution_per90,
    sample_reliability,
    reliable_goal_contribution_per90,
    international_goal_rate_reliable,
    top_league_star_power_raw,
    player_star_power_index,
    has_transfermarkt_match,
    has_top_league_form
from ranked
