with source as (
    select *
    from read_csv_auto(
        '{{ var("external_raw_data_path") }}/transfermarkt_competitions.csv',
        header = true,
        normalize_names = true
    )
)

select
    trim(cast(competition_id as varchar)) as competition_id,
    trim(cast(competition_code as varchar)) as competition_code,
    trim(cast(name as varchar)) as competition_name,
    trim(cast(sub_type as varchar)) as sub_type,
    trim(cast(type as varchar)) as competition_type,
    try_cast(country_id as integer) as country_id,
    trim(cast(country_name as varchar)) as country_name,
    trim(cast(domestic_league_code as varchar)) as domestic_league_code,
    trim(cast(confederation as varchar)) as confederation,
    try_cast(total_clubs as integer) as total_clubs,
    trim(cast(url as varchar)) as transfermarkt_url,
    trim(cast(source_dataset as varchar)) as source_dataset,
    trim(cast(source_url as varchar)) as source_url,
    try_cast(downloaded_at_utc as timestamp) as downloaded_at_utc
from source
