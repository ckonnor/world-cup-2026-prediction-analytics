with matches_before_tournament as (
    select
        *,
        row_number() over (
            partition by team_name
            order by match_date desc, result_id desc
        ) as recency_rank
    from {{ ref('int_historical_team_match_results') }}
    where match_date < cast('{{ var("tournament_start_date") }}' as date)
),

aggregated as (
    select
        team_name,
        count(*) as historical_matches,
        max(match_date) as latest_match_date,
        sum(case when recency_rank <= 10 then 1 else 0 end) as last_10_matches,
        avg(case when recency_rank <= 10 then points end) as last_10_points_per_match,
        avg(case when recency_rank <= 10 then goal_difference end) as last_10_goal_diff_per_match,
        avg(case when recency_rank <= 10 then goals_for end) as last_10_goals_for_per_match,
        avg(case when recency_rank <= 10 then goals_against end) as last_10_goals_against_per_match,
        sum(case when recency_rank <= 10 and match_result = 'win' then 1 else 0 end) as last_10_wins,
        sum(case when recency_rank <= 10 and match_result = 'draw' then 1 else 0 end) as last_10_draws,
        sum(case when recency_rank <= 10 and match_result = 'loss' then 1 else 0 end) as last_10_losses,
        sum(case when recency_rank <= 5 then 1 else 0 end) as last_5_matches,
        avg(case when recency_rank <= 5 then points end) as last_5_points_per_match,
        avg(case when recency_rank <= 5 then goal_difference end) as last_5_goal_diff_per_match,
        avg(case when recency_rank <= 5 then goals_for end) as last_5_goals_for_per_match,
        avg(case when recency_rank <= 5 then goals_against end) as last_5_goals_against_per_match,
        date_diff('day', max(match_date), cast('{{ var("tournament_start_date") }}' as date)) as days_since_latest_match
    from matches_before_tournament
    group by 1
)

select
    team_name,
    historical_matches,
    latest_match_date,
    days_since_latest_match,
    last_10_matches,
    round(last_10_points_per_match, 3) as last_10_points_per_match,
    round(last_10_goal_diff_per_match, 3) as last_10_goal_diff_per_match,
    round(last_10_goals_for_per_match, 3) as last_10_goals_for_per_match,
    round(last_10_goals_against_per_match, 3) as last_10_goals_against_per_match,
    last_10_wins,
    last_10_draws,
    last_10_losses,
    last_5_matches,
    round(last_5_points_per_match, 3) as last_5_points_per_match,
    round(last_5_goal_diff_per_match, 3) as last_5_goal_diff_per_match,
    round(last_5_goals_for_per_match, 3) as last_5_goals_for_per_match,
    round(last_5_goals_against_per_match, 3) as last_5_goals_against_per_match
from aggregated
