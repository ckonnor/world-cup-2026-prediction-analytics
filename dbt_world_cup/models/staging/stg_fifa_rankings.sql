with source as (
    select *
    from read_csv_auto(
        '{{ var("external_raw_data_path") }}/fifa_rankings.csv',
        header = true,
        normalize_names = true
    )
)

select
    try_cast(ranking_date as date) as ranking_date,
    {{ canonical_team_name('team_name') }} as team_name,
    upper(trim(cast(country_code as varchar))) as country_code,
    try_cast(rank as integer) as fifa_rank,
    try_cast(total_points as double) as fifa_points,
    try_cast(previous_rank as integer) as previous_fifa_rank,
    try_cast(previous_points as double) as previous_fifa_points,
    trim(cast(confederation as varchar)) as confederation,
    trim(cast(source_system as varchar)) as source_system,
    trim(cast(source_url as varchar)) as source_url,
    try_cast(downloaded_at_utc as timestamp) as downloaded_at_utc
from source
where try_cast(ranking_date as date) is not null
    and try_cast(rank as integer) is not null
    and try_cast(total_points as double) is not null
