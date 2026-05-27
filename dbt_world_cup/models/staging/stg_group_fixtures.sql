with source as (
    select *
    from read_csv_auto(
        '{{ var("raw_data_path") }}/group_fixtures.csv',
        header = true,
        normalize_names = true
    )
)

select
    cast(match_id as varchar) as match_id,
    upper(trim(cast(_group as varchar))) as group_letter,
    trim(cast(home_team as varchar)) as home_team,
    trim(cast(away_team as varchar)) as away_team,
    try_cast(date_utc as timestamp) as match_date_utc,
    trim(cast(venue as varchar)) as venue
from source
