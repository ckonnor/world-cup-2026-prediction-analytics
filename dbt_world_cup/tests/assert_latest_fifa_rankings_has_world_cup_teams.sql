with world_cup_teams as (
    select distinct team_model_name as team_name
    from {{ ref('dim_teams') }}
)

select
    world_cup_teams.team_name
from world_cup_teams
left join {{ ref('mart_latest_fifa_rankings') }} as rankings
    on world_cup_teams.team_name = rankings.team_name
where rankings.team_name is null
