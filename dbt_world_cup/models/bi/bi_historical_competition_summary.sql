select
    extract(year from match_date) as match_year,
    tournament,
    count(*) as matches,
    round(avg(home_score + away_score), 3) as avg_total_goals,
    round(avg(abs(home_score - away_score)), 3) as avg_goal_margin,
    round(avg(case when match_outcome = 'home' then 1 else 0 end), 3) as home_win_rate,
    round(avg(case when match_outcome = 'away' then 1 else 0 end), 3) as away_win_rate,
    round(avg(case when match_outcome = 'draw' then 1 else 0 end), 3) as draw_rate,
    round(avg(case when neutral then 1 else 0 end), 3) as neutral_match_rate,
    round(avg(case when has_complete_fifa_rankings then 1 else 0 end), 3) as fifa_feature_coverage,
    round(avg(case when has_external_match_features then 1 else 0 end), 3) as external_feature_coverage
from {{ ref('features_historical_match_training') }}
group by 1, 2
