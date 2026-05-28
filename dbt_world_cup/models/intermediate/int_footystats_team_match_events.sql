with matches as (
    select *
    from {{ ref('stg_footystats_match_stats') }}
    where status = 'complete'
        and home_corners >= 0
        and away_corners >= 0
        and home_yellow_cards >= 0
        and away_yellow_cards >= 0
        and home_red_cards >= 0
        and away_red_cards >= 0
),

team_rows as (
    select
        source_match_id,
        source_competition,
        source_type,
        source_weight,
        match_date,
        home_team_name as team_name,
        away_team_name as opponent_name,
        true as is_home_team,
        home_goals as goals_for,
        away_goals as goals_against,
        home_corners as corners_for,
        away_corners as corners_against,
        home_yellow_cards as yellow_cards_for,
        away_yellow_cards as yellow_cards_against,
        home_red_cards as red_cards_for,
        away_red_cards as red_cards_against
    from matches

    union all

    select
        source_match_id,
        source_competition,
        source_type,
        source_weight,
        match_date,
        away_team_name as team_name,
        home_team_name as opponent_name,
        false as is_home_team,
        away_goals as goals_for,
        home_goals as goals_against,
        away_corners as corners_for,
        home_corners as corners_against,
        away_yellow_cards as yellow_cards_for,
        home_yellow_cards as yellow_cards_against,
        away_red_cards as red_cards_for,
        home_red_cards as red_cards_against
    from matches
)

select
    *,
    corners_for + corners_against as total_corners,
    yellow_cards_for + yellow_cards_against as total_yellow_cards,
    red_cards_for + red_cards_against as total_red_cards
from team_rows
