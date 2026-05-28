with source as (
    select *
    from read_csv_auto(
        '{{ var("external_raw_data_path") }}/world_cup_2026_squads.csv',
        header = true,
        normalize_names = true
    )
)

select
    trim(cast(source_team_name as varchar)) as team_name,
    trim(cast(squad_status as varchar)) as squad_status,
    cast(source_player_count as integer) as source_player_count,
    cast(shirt_number as integer) as shirt_number,
    upper(trim(cast(position as varchar))) as position,
    trim(cast(player_name as varchar)) as player_name,
    {{ normalized_name_key('player_name') }} as player_name_key,
    cast(is_captain as boolean) as is_captain,
    try_cast(date_of_birth as date) as date_of_birth,
    cast(age as integer) as age,
    cast(caps as integer) as caps,
    cast(goals as integer) as goals,
    trim(cast(club as varchar)) as club,
    trim(cast(source_url as varchar)) as source_url,
    try_cast(downloaded_at_utc as timestamp) as downloaded_at_utc
from source
