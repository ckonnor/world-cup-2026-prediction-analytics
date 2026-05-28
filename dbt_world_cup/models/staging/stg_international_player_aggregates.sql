with source as (
    select *
    from read_csv_auto(
        '{{ var("external_raw_data_path") }}/international_player_aggregates.csv',
        header = true,
        normalize_names = true
    )
)

select
    {{ canonical_team_name('country') }} as team_name,
    try_cast(fifa_version as integer) as fifa_version,
    try_cast(num_players as integer) as num_players,
    try_cast(avg_overall as double) as avg_overall,
    try_cast(max_overall as double) as max_overall,
    try_cast(avg_pace as double) as avg_pace,
    try_cast(avg_shooting as double) as avg_shooting,
    try_cast(avg_passing as double) as avg_passing,
    try_cast(avg_dribbling as double) as avg_dribbling,
    try_cast(avg_defending as double) as avg_defending,
    try_cast(avg_physic as double) as avg_physic,
    try_cast(avg_attack_overall as double) as avg_attack_overall,
    try_cast(avg_defense_overall as double) as avg_defense_overall,
    trim(cast(source_dataset as varchar)) as source_dataset,
    trim(cast(source_url as varchar)) as source_url,
    try_cast(downloaded_at_utc as timestamp) as downloaded_at_utc
from source
where try_cast(fifa_version as integer) is not null
