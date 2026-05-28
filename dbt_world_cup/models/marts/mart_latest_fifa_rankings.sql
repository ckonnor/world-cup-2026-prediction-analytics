with rankings as (
    select *
    from {{ ref('stg_fifa_rankings') }}
),

latest as (
    select
        *,
        row_number() over (
            partition by team_name
            order by ranking_date desc
        ) as ranking_recency
    from rankings
)

select
    team_name,
    country_code,
    ranking_date,
    fifa_rank,
    fifa_points,
    previous_fifa_rank,
    previous_fifa_points,
    confederation,
    source_system,
    source_url
from latest
where ranking_recency = 1
