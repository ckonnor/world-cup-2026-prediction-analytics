with unmatched as (
    select
        shootouts.shootout_id,
        shootouts.match_date,
        shootouts.home_team,
        shootouts.away_team
    from {{ ref('stg_shootouts') }} as shootouts
    left join {{ ref('stg_international_results') }} as results
        on shootouts.match_date = results.match_date
        and shootouts.home_team = results.home_team
        and shootouts.away_team = results.away_team
    where results.result_id is null
),

summary as (
    select count(*) as unmatched_shootout_rows
    from unmatched
)

select *
from summary
where unmatched_shootout_rows > 1
