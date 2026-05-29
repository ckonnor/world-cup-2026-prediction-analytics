with ranked as (
    select
        *,
        row_number() over (
            partition by team_name
            order by fifa_version desc
        ) as player_strength_rank
    from {{ ref('stg_international_player_aggregates') }}
),

external_strength as (
    select *
    from ranked
    where player_strength_rank = 1
),

top_league_player_strength as (
    select *
    from {{ ref('mart_top_league_player_strength') }}
)

select
    external_strength.team_name,
    external_strength.fifa_version,
    external_strength.num_players,
    external_strength.avg_overall,
    external_strength.max_overall,
    external_strength.avg_pace,
    external_strength.avg_shooting,
    external_strength.avg_passing,
    external_strength.avg_dribbling,
    external_strength.avg_defending,
    external_strength.avg_physic,
    external_strength.avg_attack_overall,
    external_strength.avg_defense_overall,
    coalesce(
        top_league_player_strength.player_star_power_index,
        0.30 * external_strength.avg_overall
            + 0.35 * external_strength.max_overall
            + 0.15 * coalesce(
                external_strength.avg_attack_overall,
                external_strength.avg_overall
            )
            + 0.10 * coalesce(
                external_strength.avg_shooting,
                external_strength.avg_attack_overall,
                external_strength.avg_overall
            )
            + 0.05 * coalesce(external_strength.avg_passing, external_strength.avg_overall)
            + 0.05 * coalesce(external_strength.avg_pace, external_strength.avg_overall)
    ) as player_star_power_index,
    coalesce(
        top_league_player_strength.superstar_gap,
        external_strength.max_overall - external_strength.avg_overall
    ) as superstar_gap,
    coalesce(
        top_league_player_strength.attacking_star_power_index,
        0.40 * coalesce(
            external_strength.avg_attack_overall,
            external_strength.avg_overall
        )
            + 0.30 * coalesce(
                external_strength.avg_shooting,
                external_strength.avg_attack_overall,
                external_strength.avg_overall
            )
            + 0.15 * coalesce(external_strength.avg_passing, external_strength.avg_overall)
            + 0.15 * coalesce(external_strength.avg_pace, external_strength.avg_overall)
    ) as attacking_star_power_index,
    top_league_player_strength.transfermarkt_match_coverage,
    top_league_player_strength.top_league_form_coverage,
    external_strength.source_dataset,
    external_strength.source_url,
    external_strength.downloaded_at_utc
from external_strength
left join top_league_player_strength
    on external_strength.team_name = top_league_player_strength.team_name
