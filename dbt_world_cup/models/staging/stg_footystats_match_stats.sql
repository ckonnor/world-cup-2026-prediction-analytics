with source as (
    select *
    from read_csv_auto(
        '{{ var("external_raw_data_path") }}/footystats_match_stats.csv',
        header = true,
        normalize_names = true
    )
)

select
    trim(cast(source_match_id as varchar)) as source_match_id,
    trim(cast(source_competition as varchar)) as source_competition,
    trim(cast(source_type as varchar)) as source_type,
    cast(source_weight as double) as source_weight,
    cast(comp_id as integer) as comp_id,
    trim(cast(source_url as varchar)) as source_url,
    try_cast(downloaded_at_utc as timestamp) as downloaded_at_utc,
    cast(source_row_number as integer) as source_row_number,
    trim(cast(match_date_gmt_raw as varchar)) as match_date_gmt_raw,
    try_cast(match_date as date) as match_date,
    lower(trim(cast(status as varchar))) as status,
    trim(cast(home_team_name as varchar)) as home_team_name_raw,
    trim(cast(away_team_name as varchar)) as away_team_name_raw,
    {{ canonical_team_name('home_team_name') }} as home_team_name,
    {{ canonical_team_name('away_team_name') }} as away_team_name,
    cast(home_goals as integer) as home_goals,
    cast(away_goals as integer) as away_goals,
    cast(home_corners as integer) as home_corners,
    cast(away_corners as integer) as away_corners,
    cast(home_yellow_cards as integer) as home_yellow_cards,
    cast(away_yellow_cards as integer) as away_yellow_cards,
    cast(home_red_cards as integer) as home_red_cards,
    cast(away_red_cards as integer) as away_red_cards
from source
