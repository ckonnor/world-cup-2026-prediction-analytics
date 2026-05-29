with source as (
    select *
    from read_csv_auto(
        '{{ var("external_raw_data_path") }}/transfermarkt_players.csv',
        header = true,
        normalize_names = true
    )
)

select
    cast(player_id as bigint) as player_id,
    trim(cast(name as varchar)) as player_name,
    {{ normalized_name_key('name') }} as player_name_key,
    try_cast(last_season as integer) as last_season,
    try_cast(current_club_id as bigint) as current_club_id,
    trim(cast(country_of_citizenship as varchar)) as country_of_citizenship,
    {{ canonical_team_name('country_of_citizenship') }} as citizenship_team_name,
    try_cast(date_of_birth as date) as date_of_birth,
    trim(cast(sub_position as varchar)) as sub_position,
    trim(cast(position as varchar)) as position_group,
    trim(cast(foot as varchar)) as foot,
    try_cast(height_in_cm as double) as height_in_cm,
    try_cast(international_caps as double) as international_caps,
    try_cast(international_goals as double) as international_goals,
    try_cast(current_national_team_id as bigint) as current_national_team_id,
    trim(cast(url as varchar)) as player_url,
    trim(cast(current_club_domestic_competition_id as varchar))
        as current_club_domestic_competition_id,
    trim(cast(current_club_name as varchar)) as current_club_name,
    try_cast(market_value_in_eur as double) as market_value_in_eur,
    try_cast(highest_market_value_in_eur as double) as highest_market_value_in_eur,
    trim(cast(source_dataset as varchar)) as source_dataset,
    trim(cast(source_url as varchar)) as source_url,
    try_cast(downloaded_at_utc as timestamp) as downloaded_at_utc
from source
