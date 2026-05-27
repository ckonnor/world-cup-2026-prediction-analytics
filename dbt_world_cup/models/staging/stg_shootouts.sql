with source as (
    select *
    from read_csv_auto(
        '{{ var("external_raw_data_path") }}/shootouts.csv',
        header = true,
        normalize_names = true
    )
)

select
    md5(
        concat_ws(
            '|',
            cast(date as varchar),
            cast(home_team as varchar),
            cast(away_team as varchar),
            cast(winner as varchar)
        )
    ) as shootout_id,
    cast(date as date) as match_date,
    trim(cast(home_team as varchar)) as home_team,
    trim(cast(away_team as varchar)) as away_team,
    trim(cast(winner as varchar)) as shootout_winner,
    trim(cast(first_shooter as varchar)) as first_shooter
from source
