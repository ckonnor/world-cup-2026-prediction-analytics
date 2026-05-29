with squad_player_power as (
    select *
    from {{ ref('int_world_cup_squad_player_power') }}
),

ranked as (
    select
        *,
        row_number() over (
            partition by team_model_name
            order by player_star_power_index desc, top_league_minutes desc nulls last, player_name
        ) as player_power_rank
    from squad_player_power
),

aggregated as (
    select
        team_model_name as team_name,
        count(*) as squad_players,
        sum(case when has_transfermarkt_match then 1 else 0 end)
            as transfermarkt_matched_players,
        sum(case when has_top_league_form then 1 else 0 end)
            as top_league_form_players,
        max(player_star_power_index) as max_player_star_power_index,
        avg(case when player_power_rank <= 5 then player_star_power_index end)
            as avg_top_5_player_star_power,
        avg(case when player_power_rank <= 10 then player_star_power_index end)
            as avg_top_10_player_star_power,
        avg(
            case
                when position in ('FW', 'MF') and player_power_rank <= 10
                    then player_star_power_index
            end
        ) as avg_top_attacking_player_star_power,
        max(
            case
                when position in ('FW', 'MF') then player_star_power_index
            end
        ) as max_attacking_player_star_power
    from ranked
    group by 1
)

select
    team_name,
    squad_players,
    transfermarkt_matched_players,
    top_league_form_players,
    round(transfermarkt_matched_players / nullif(squad_players, 0), 3)
        as transfermarkt_match_coverage,
    round(top_league_form_players / nullif(squad_players, 0), 3)
        as top_league_form_coverage,
    round(
        0.45 * coalesce(avg_top_5_player_star_power, 0)
        + 0.35 * coalesce(max_player_star_power_index, 0)
        + 0.20 * coalesce(avg_top_10_player_star_power, avg_top_5_player_star_power, 0),
        3
    ) as player_star_power_index,
    round(
        coalesce(max_player_star_power_index, 0)
        - coalesce(avg_top_10_player_star_power, avg_top_5_player_star_power, 0),
        3
    ) as superstar_gap,
    round(
        0.60 * coalesce(avg_top_attacking_player_star_power, avg_top_5_player_star_power, 0)
        + 0.40 * coalesce(max_attacking_player_star_power, max_player_star_power_index, 0),
        3
    ) as attacking_star_power_index,
    round(max_player_star_power_index, 3) as max_player_star_power_index,
    round(avg_top_5_player_star_power, 3) as avg_top_5_player_star_power,
    round(avg_top_10_player_star_power, 3) as avg_top_10_player_star_power
from aggregated
