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
    source_dataset,
    source_url,
    downloaded_at_utc
from ranked
where player_strength_rank = 1
