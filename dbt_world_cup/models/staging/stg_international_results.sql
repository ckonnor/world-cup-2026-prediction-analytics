with source as (
    select *
    from read_csv_auto(
        '{{ var("external_raw_data_path") }}/results.csv',
        header = true,
        normalize_names = true,
        nullstr = 'NA',
        sample_size = -1
    )
)

select
    md5(
        concat_ws(
            '|',
            cast(date as varchar),
            cast(home_team as varchar),
            cast(away_team as varchar),
            cast(home_score as varchar),
            cast(away_score as varchar),
            cast(tournament as varchar)
        )
    ) as result_id,
    cast(date as date) as match_date,
    trim(cast(home_team as varchar)) as home_team,
    trim(cast(away_team as varchar)) as away_team,
    cast(home_score as integer) as home_score,
    cast(away_score as integer) as away_score,
    trim(cast(tournament as varchar)) as tournament,
    trim(cast(city as varchar)) as city,
    trim(cast(country as varchar)) as country,
    cast(neutral as boolean) as neutral
from source
where home_score is not null
    and away_score is not null
