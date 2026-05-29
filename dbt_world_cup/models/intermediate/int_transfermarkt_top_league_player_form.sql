with league_weights as (
    select *
    from (
        values
            ('GB1', 'Premier League', 1, 91.9, 1.000),
            ('IT1', 'Serie A', 2, 86.1, 0.937),
            ('ES1', 'LaLiga', 3, 86.0, 0.936),
            ('FR1', 'Ligue 1', 4, 85.5, 0.930),
            ('L1', 'Bundesliga', 5, 85.4, 0.929),
            ('BE1', 'Belgian Pro League', 6, 81.5, 0.887),
            ('PO1', 'Liga Portugal', 8, 80.7, 0.878),
            ('BRA1', 'Brazil Serie A', 9, 80.0, 0.870),
            ('MLS1', 'MLS', 10, 79.3, 0.863)
    ) as weights(
        competition_id,
        league_name,
        league_rank,
        league_rating,
        league_weight
    )
),

players as (
    select *
    from {{ ref('stg_transfermarkt_players') }}
),

appearances as (
    select *
    from {{ ref('stg_transfermarkt_appearances') }}
    where appearance_date >= date '2022-12-19'
),

top_league_appearances as (
    select
        appearances.player_id,
        appearances.appearance_date,
        appearances.competition_id,
        league_weights.league_name,
        league_weights.league_rank,
        league_weights.league_rating,
        league_weights.league_weight,
        appearances.minutes_played,
        appearances.goals,
        appearances.assists,
        appearances.yellow_cards,
        appearances.red_cards
    from appearances
    inner join league_weights
        on appearances.competition_id = league_weights.competition_id
),

appearance_rollup as (
    select
        player_id,
        count(*) as top_league_appearances,
        count(distinct competition_id) as top_leagues_played,
        min(league_rank) as best_league_rank,
        max(league_rating) as best_league_rating,
        string_agg(distinct league_name, '; ' order by league_name) as top_league_names,
        sum(minutes_played) as top_league_minutes,
        sum(minutes_played) / 90.0 as top_league_nineties,
        sum(minutes_played / 90.0 * league_weight) as league_weighted_nineties,
        sum(goals) as top_league_goals,
        sum(assists) as top_league_assists,
        sum(yellow_cards) as top_league_yellow_cards,
        sum(red_cards) as top_league_red_cards,
        sum(goals * league_weight) as league_weighted_goals,
        sum(assists * league_weight) as league_weighted_assists
    from top_league_appearances
    group by 1
),

current_league_context as (
    select
        players.player_id,
        league_weights.league_name as current_top_league_name,
        league_weights.league_rank as current_top_league_rank,
        league_weights.league_rating as current_top_league_rating,
        league_weights.league_weight as current_top_league_weight
    from players
    left join league_weights
        on players.current_club_domestic_competition_id = league_weights.competition_id
),

base as (
    select
        players.player_id,
        players.player_name,
        players.player_name_key,
        players.citizenship_team_name,
        players.country_of_citizenship,
        players.position_group,
        players.sub_position,
        players.current_club_name,
        players.current_club_domestic_competition_id,
        current_league_context.current_top_league_name,
        current_league_context.current_top_league_rank,
        current_league_context.current_top_league_rating,
        coalesce(players.market_value_in_eur, 0) as market_value_in_eur,
        coalesce(players.highest_market_value_in_eur, 0) as highest_market_value_in_eur,
        coalesce(players.international_caps, 0) as transfermarkt_international_caps,
        coalesce(players.international_goals, 0) as transfermarkt_international_goals,
        coalesce(appearance_rollup.top_league_appearances, 0) as top_league_appearances,
        coalesce(appearance_rollup.top_leagues_played, 0) as top_leagues_played,
        appearance_rollup.best_league_rank,
        appearance_rollup.best_league_rating,
        appearance_rollup.top_league_names,
        coalesce(appearance_rollup.top_league_minutes, 0) as top_league_minutes,
        coalesce(appearance_rollup.top_league_nineties, 0) as top_league_nineties,
        coalesce(appearance_rollup.league_weighted_nineties, 0) as league_weighted_nineties,
        coalesce(appearance_rollup.top_league_goals, 0) as top_league_goals,
        coalesce(appearance_rollup.top_league_assists, 0) as top_league_assists,
        coalesce(appearance_rollup.top_league_yellow_cards, 0) as top_league_yellow_cards,
        coalesce(appearance_rollup.top_league_red_cards, 0) as top_league_red_cards,
        coalesce(appearance_rollup.league_weighted_goals, 0) as league_weighted_goals,
        coalesce(appearance_rollup.league_weighted_assists, 0) as league_weighted_assists
    from players
    left join appearance_rollup
        on players.player_id = appearance_rollup.player_id
    left join current_league_context
        on players.player_id = current_league_context.player_id
),

signals as (
    select
        *,
        case
            when top_league_nineties > 0
                then league_weighted_goals / top_league_nineties
            else 0
        end as league_weighted_goals_per90,
        case
            when top_league_nineties > 0
                then league_weighted_assists / top_league_nineties
            else 0
        end as league_weighted_assists_per90,
        case
            when top_league_nineties > 0
                then (
                    league_weighted_goals + 0.75 * league_weighted_assists
                ) / top_league_nineties
            else 0
        end as league_weighted_goal_contribution_per90,
        least(1.0, sqrt(top_league_nineties / 20.0)) as sample_reliability,
        case
            when transfermarkt_international_caps > 0
                then transfermarkt_international_goals
                    / transfermarkt_international_caps
                    * least(1.0, transfermarkt_international_caps / 30.0)
            else 0
        end as international_goal_rate_reliable,
        ln(1 + market_value_in_eur / 1000000.0) as current_market_value_log,
        ln(1 + highest_market_value_in_eur / 1000000.0) as peak_market_value_log
    from base
    where top_league_nineties > 0
        or market_value_in_eur > 0
        or highest_market_value_in_eur > 0
        or transfermarkt_international_caps > 0
),

standardized as (
    select
        *,
        league_weighted_goal_contribution_per90 * sample_reliability
            as reliable_goal_contribution_per90,
        case
            when stddev_samp(
                league_weighted_goal_contribution_per90 * sample_reliability
            ) over () = 0 then 0
            else (
                league_weighted_goal_contribution_per90 * sample_reliability
                - avg(
                    league_weighted_goal_contribution_per90 * sample_reliability
                ) over ()
            ) / stddev_samp(
                league_weighted_goal_contribution_per90 * sample_reliability
            ) over ()
        end as production_rate_z,
        case
            when stddev_samp(current_market_value_log) over () = 0 then 0
            else (current_market_value_log - avg(current_market_value_log) over ())
                / stddev_samp(current_market_value_log) over ()
        end as current_market_value_z,
        case
            when stddev_samp(peak_market_value_log) over () = 0 then 0
            else (peak_market_value_log - avg(peak_market_value_log) over ())
                / stddev_samp(peak_market_value_log) over ()
        end as peak_market_value_z,
        case
            when stddev_samp(international_goal_rate_reliable) over () = 0 then 0
            else (
                international_goal_rate_reliable
                - avg(international_goal_rate_reliable) over ()
            ) / stddev_samp(international_goal_rate_reliable) over ()
        end as international_goal_rate_z,
        case
            when stddev_samp(league_weighted_nineties) over () = 0 then 0
            else (league_weighted_nineties - avg(league_weighted_nineties) over ())
                / stddev_samp(league_weighted_nineties) over ()
        end as league_minutes_z
    from signals
),

scored as (
    select
        *,
        (
            0.35 * production_rate_z
            + 0.45 * current_market_value_z
            + 0.10 * peak_market_value_z
            + 0.05 * international_goal_rate_z
            + 0.05 * league_minutes_z
        ) as top_league_star_power_raw
    from standardized
)

select
    player_id,
    player_name,
    player_name_key,
    citizenship_team_name,
    country_of_citizenship,
    position_group,
    sub_position,
    current_club_name,
    current_club_domestic_competition_id,
    current_top_league_name,
    current_top_league_rank,
    current_top_league_rating,
    market_value_in_eur,
    highest_market_value_in_eur,
    transfermarkt_international_caps,
    transfermarkt_international_goals,
    top_league_appearances,
    top_leagues_played,
    best_league_rank,
    best_league_rating,
    top_league_names,
    top_league_minutes,
    round(top_league_nineties, 3) as top_league_nineties,
    round(league_weighted_nineties, 3) as league_weighted_nineties,
    top_league_goals,
    top_league_assists,
    top_league_yellow_cards,
    top_league_red_cards,
    round(league_weighted_goals_per90, 3) as league_weighted_goals_per90,
    round(league_weighted_assists_per90, 3) as league_weighted_assists_per90,
    round(league_weighted_goal_contribution_per90, 3)
        as league_weighted_goal_contribution_per90,
    round(sample_reliability, 3) as sample_reliability,
    round(reliable_goal_contribution_per90, 3) as reliable_goal_contribution_per90,
    round(international_goal_rate_reliable, 3) as international_goal_rate_reliable,
    round(top_league_star_power_raw, 3) as top_league_star_power_raw,
    round(least(100, greatest(0, 50 + 6 * top_league_star_power_raw)), 1)
        as player_star_power_index
from scored
