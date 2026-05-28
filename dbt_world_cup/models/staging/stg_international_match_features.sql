with source as (
    select *
    from read_csv_auto(
        '{{ var("external_raw_data_path") }}/international_match_features.csv',
        header = true,
        normalize_names = true
    )
),

cleaned as (
    select
        try_cast(_date as date) as match_date,
        {{ canonical_team_name('_home_team') }} as home_team,
        {{ canonical_team_name('_away_team') }} as away_team,
        trim(cast(_tournament as varchar)) as tournament,
        try_cast(home_goals as integer) as home_goals,
        try_cast(away_goals as integer) as away_goals,
        try_cast(home_elo as double) as external_home_elo,
        try_cast(away_elo as double) as external_away_elo,
        try_cast(elo_diff as double) as external_elo_diff,
        try_cast(home_avg_overall as double) as external_home_avg_overall,
        try_cast(home_max_overall as double) as external_home_max_overall,
        try_cast(home_avg_attack as double) as external_home_avg_attack,
        try_cast(home_avg_defense as double) as external_home_avg_defense,
        try_cast(home_avg_pace as double) as external_home_avg_pace,
        try_cast(home_avg_shooting as double) as external_home_avg_shooting,
        try_cast(home_avg_passing as double) as external_home_avg_passing,
        try_cast(away_avg_overall as double) as external_away_avg_overall,
        try_cast(away_max_overall as double) as external_away_max_overall,
        try_cast(away_avg_attack as double) as external_away_avg_attack,
        try_cast(away_avg_defense as double) as external_away_avg_defense,
        try_cast(away_avg_pace as double) as external_away_avg_pace,
        try_cast(away_avg_shooting as double) as external_away_avg_shooting,
        try_cast(away_avg_passing as double) as external_away_avg_passing,
        try_cast(overall_diff as double) as external_overall_diff,
        try_cast(attack_diff as double) as external_attack_diff,
        try_cast(defense_diff as double) as external_defense_diff,
        try_cast(home_form_scored as double) as external_home_form_scored,
        try_cast(home_form_conceded as double) as external_home_form_conceded,
        try_cast(home_form_win_rate as double) as external_home_form_win_rate,
        try_cast(away_form_scored as double) as external_away_form_scored,
        try_cast(away_form_conceded as double) as external_away_form_conceded,
        try_cast(away_form_win_rate as double) as external_away_form_win_rate,
        try_cast(is_neutral as integer) as external_is_neutral,
        try_cast(is_world_cup as integer) as external_is_world_cup,
        try_cast(is_continental as integer) as external_is_continental,
        trim(cast(source_dataset as varchar)) as source_dataset,
        trim(cast(source_url as varchar)) as source_url,
        try_cast(downloaded_at_utc as timestamp) as downloaded_at_utc
    from source
    where try_cast(_date as date) is not null
        and try_cast(home_goals as integer) is not null
        and try_cast(away_goals as integer) is not null
),

deduped as (
    select
        *,
        row_number() over (
            partition by match_date, home_team, away_team, home_goals, away_goals
            order by tournament
        ) as match_feature_rank
    from cleaned
)

select * exclude (match_feature_rank)
from deduped
where match_feature_rank = 1
