with source as (
    select
        cast(match_id as varchar) as match_id,
        upper(trim(cast(_group as varchar))) as group_letter,
        trim(cast(home_team as varchar)) as home_team_raw,
        trim(cast(away_team as varchar)) as away_team_raw,
        try_cast(date_utc as timestamp) as match_date_utc,
        trim(cast(venue as varchar)) as venue
    from read_csv_auto(
        '{{ var("raw_data_path") }}/group_fixtures.csv',
        header = true,
        normalize_names = true
    )
),

team_resolution as (
    select *
    from {{ ref('team_name_resolution') }}
)

select
    source.match_id,
    source.group_letter,
    source.home_team_raw,
    source.away_team_raw,
    coalesce(home_resolution.display_team_name, source.home_team_raw) as home_team,
    coalesce(away_resolution.display_team_name, source.away_team_raw) as away_team,
    coalesce(
        home_resolution.model_team_name,
        case when source.home_team_raw like '%Ivoire%' then 'Ivory Coast' else source.home_team_raw end
    ) as home_team_model_name,
    coalesce(
        away_resolution.model_team_name,
        case when source.away_team_raw like '%Ivoire%' then 'Ivory Coast' else source.away_team_raw end
    ) as away_team_model_name,
    home_resolution.raw_team_name is not null as home_team_was_resolved,
    away_resolution.raw_team_name is not null as away_team_was_resolved,
    source.match_date_utc,
    source.venue
from source
left join team_resolution as home_resolution
    on source.home_team_raw = home_resolution.raw_team_name
left join team_resolution as away_resolution
    on source.away_team_raw = away_resolution.raw_team_name
