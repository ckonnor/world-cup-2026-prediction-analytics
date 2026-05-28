with matches as (
    select *
    from {{ ref('stg_international_results') }}
),

match_teams as (
    select
        result_id,
        match_date,
        home_team as team_name,
        'home' as side
    from matches

    union all

    select
        result_id,
        match_date,
        away_team as team_name,
        'away' as side
    from matches
),

rankings as (
    select *
    from {{ ref('stg_fifa_rankings') }}
),

point_in_time_rankings as (
    select
        match_teams.result_id,
        match_teams.side,
        rankings.ranking_date,
        rankings.fifa_rank,
        rankings.fifa_points,
        row_number() over (
            partition by match_teams.result_id, match_teams.side
            order by rankings.ranking_date desc
        ) as ranking_recency
    from match_teams
    left join rankings
        on match_teams.team_name = rankings.team_name
        and rankings.ranking_date <= match_teams.match_date
),

home_rankings as (
    select *
    from point_in_time_rankings
    where side = 'home'
        and ranking_recency = 1
),

away_rankings as (
    select *
    from point_in_time_rankings
    where side = 'away'
        and ranking_recency = 1
)

select
    matches.result_id,
    home_rankings.ranking_date as home_fifa_ranking_date,
    away_rankings.ranking_date as away_fifa_ranking_date,
    home_rankings.fifa_rank as home_fifa_rank,
    away_rankings.fifa_rank as away_fifa_rank,
    home_rankings.fifa_points as home_fifa_points,
    away_rankings.fifa_points as away_fifa_points,
    home_rankings.fifa_rank - away_rankings.fifa_rank as fifa_rank_diff,
    home_rankings.fifa_points - away_rankings.fifa_points as fifa_points_diff,
    home_rankings.fifa_rank is not null
        and away_rankings.fifa_rank is not null as has_complete_fifa_rankings
from matches
left join home_rankings
    on matches.result_id = home_rankings.result_id
left join away_rankings
    on matches.result_id = away_rankings.result_id
