with source as (
    select *
    from read_csv_auto(
        '{{ var("external_raw_data_path") }}/transfermarkt_appearances.csv',
        header = true,
        normalize_names = true
    )
)

select
    trim(cast(appearance_id as varchar)) as appearance_id,
    cast(game_id as bigint) as game_id,
    cast(player_id as bigint) as player_id,
    cast(player_club_id as bigint) as player_club_id,
    cast(player_current_club_id as bigint) as player_current_club_id,
    try_cast(date as date) as appearance_date,
    trim(cast(player_name as varchar)) as player_name,
    {{ normalized_name_key('player_name') }} as player_name_key,
    trim(cast(competition_id as varchar)) as competition_id,
    cast(yellow_cards as integer) as yellow_cards,
    cast(red_cards as integer) as red_cards,
    cast(goals as integer) as goals,
    cast(assists as integer) as assists,
    cast(minutes_played as integer) as minutes_played,
    trim(cast(source_dataset as varchar)) as source_dataset,
    trim(cast(source_url as varchar)) as source_url,
    try_cast(downloaded_at_utc as timestamp) as downloaded_at_utc
from source
