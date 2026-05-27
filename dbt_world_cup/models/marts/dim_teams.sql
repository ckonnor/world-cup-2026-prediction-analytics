with teams as (
    select
        home_team as team_name,
        home_team_model_name as team_model_name,
        group_letter
    from {{ ref('stg_group_fixtures') }}

    union

    select
        away_team as team_name,
        away_team_model_name as team_model_name,
        group_letter
    from {{ ref('stg_group_fixtures') }}
)

select
    md5(team_name) as team_id,
    team_name,
    min(team_model_name) as team_model_name,
    min(group_letter) as group_letter
from teams
group by 1, 2
