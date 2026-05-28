with source as (
    select *
    from read_csv_auto(
        '{{ var("external_raw_data_path") }}/club_player_stats_2025_2026.csv',
        header = true,
        normalize_names = true
    )
)

select
    trim(cast(source_dataset as varchar)) as source_dataset,
    trim(cast(source_url as varchar)) as source_url,
    try_cast(downloaded_at_utc as timestamp) as downloaded_at_utc,
    trim(cast(player_name as varchar)) as player_name,
    {{ normalized_name_key('player_name') }} as player_name_key,
    trim(cast(nation_raw as varchar)) as nation_raw,
    upper(trim(cast(nation_code as varchar))) as nation_code,
    trim(cast(positions as varchar)) as positions,
    trim(cast(club_name as varchar)) as club_name,
    trim(cast(competition as varchar)) as competition,
    try_cast(age as double) as age,
    try_cast(matches_played as integer) as matches_played,
    try_cast(starts as integer) as starts,
    try_cast(minutes as double) as minutes,
    try_cast(nineties as double) as nineties,
    try_cast(goals as integer) as goals,
    try_cast(assists as integer) as assists,
    try_cast(yellow_cards as integer) as yellow_cards,
    try_cast(red_cards as integer) as red_cards,
    try_cast(second_yellow_cards as integer) as second_yellow_cards,
    try_cast(fouls_committed as integer) as fouls_committed,
    try_cast(fouls_drawn as integer) as fouls_drawn,
    try_cast(crosses as integer) as crosses,
    try_cast(tackles_won as integer) as tackles_won,
    try_cast(interceptions as integer) as interceptions
from source
