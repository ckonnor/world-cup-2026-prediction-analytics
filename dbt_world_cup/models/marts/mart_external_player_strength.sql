with ranked as (
    select
        *,
        row_number() over (
            partition by team_name
            order by fifa_version desc
        ) as player_strength_rank
    from {{ ref('stg_international_player_aggregates') }}
)

select
    team_name,
    fifa_version,
    num_players,
    avg_overall,
    max_overall,
    avg_pace,
    avg_shooting,
    avg_passing,
    avg_dribbling,
    avg_defending,
    avg_physic,
    avg_attack_overall,
    avg_defense_overall,
    0.30 * avg_overall
        + 0.35 * max_overall
        + 0.15 * coalesce(avg_attack_overall, avg_overall)
        + 0.10 * coalesce(avg_shooting, avg_attack_overall, avg_overall)
        + 0.05 * coalesce(avg_passing, avg_overall)
        + 0.05 * coalesce(avg_pace, avg_overall) as player_star_power_index,
    max_overall - avg_overall as superstar_gap,
    0.40 * coalesce(avg_attack_overall, avg_overall)
        + 0.30 * coalesce(avg_shooting, avg_attack_overall, avg_overall)
        + 0.15 * coalesce(avg_passing, avg_overall)
        + 0.15 * coalesce(avg_pace, avg_overall) as attacking_star_power_index,
    source_dataset,
    source_url,
    downloaded_at_utc
from ranked
where player_strength_rank = 1
