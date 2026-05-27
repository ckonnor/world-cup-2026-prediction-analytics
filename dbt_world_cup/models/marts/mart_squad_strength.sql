with squad_players as (
    select *
    from {{ ref('stg_world_cup_squads') }}
),

ranked as (
    select
        *,
        row_number() over (
            partition by team_name
            order by caps desc, goals desc, player_name
        ) as caps_rank,
        row_number() over (
            partition by team_name
            order by goals desc, caps desc, player_name
        ) as goals_rank
    from squad_players
),

aggregated as (
    select
        team_name,
        max(squad_status) as squad_status,
        max(source_player_count) as source_player_count,
        count(*) as squad_players,
        sum(case when position = 'GK' then 1 else 0 end) as goalkeepers,
        sum(case when position = 'DF' then 1 else 0 end) as defenders,
        sum(case when position = 'MF' then 1 else 0 end) as midfielders,
        sum(case when position = 'FW' then 1 else 0 end) as forwards,
        round(avg(age), 3) as average_age,
        sum(caps) as total_caps,
        sum(goals) as total_goals,
        sum(case when position = 'GK' then caps else 0 end) as goalkeeper_caps,
        sum(case when position = 'DF' then caps else 0 end) as defender_caps,
        sum(case when position = 'MF' then caps else 0 end) as midfielder_caps,
        sum(case when position = 'FW' then caps else 0 end) as forward_caps,
        sum(case when position in ('MF', 'FW') then goals else 0 end) as attacking_goals,
        sum(case when position in ('GK', 'DF') then caps else 0 end) as defensive_caps,
        sum(case when caps_rank <= 5 then caps else 0 end) as top_5_caps,
        sum(case when goals_rank <= 5 then goals else 0 end) as top_5_goals,
        max(caps) as max_player_caps,
        max(goals) as max_player_goals,
        sum(case when is_captain then caps else 0 end) as captain_caps
    from ranked
    group by 1
),

raw_scores as (
    select
        *,
        ln(1 + total_caps) + 0.25 * ln(1 + top_5_caps) as experience_score_raw,
        ln(1 + attacking_goals) + 0.40 * ln(1 + top_5_goals) as attacking_star_power_raw,
        ln(1 + defensive_caps) + 0.30 * ln(1 + goalkeeper_caps) as defensive_experience_raw,
        (
            0.45 * (ln(1 + total_caps) + 0.25 * ln(1 + top_5_caps))
            + 0.35 * (ln(1 + attacking_goals) + 0.40 * ln(1 + top_5_goals))
            + 0.20 * (ln(1 + defensive_caps) + 0.30 * ln(1 + goalkeeper_caps))
        ) as overall_star_power_raw
    from aggregated
),

scored as (
    select
        *,
        case
            when stddev_samp(experience_score_raw) over () = 0 then 0
            else (experience_score_raw - avg(experience_score_raw) over ())
                / stddev_samp(experience_score_raw) over ()
        end as experience_score_z,
        case
            when stddev_samp(attacking_star_power_raw) over () = 0 then 0
            else (attacking_star_power_raw - avg(attacking_star_power_raw) over ())
                / stddev_samp(attacking_star_power_raw) over ()
        end as attacking_star_power_z,
        case
            when stddev_samp(defensive_experience_raw) over () = 0 then 0
            else (defensive_experience_raw - avg(defensive_experience_raw) over ())
                / stddev_samp(defensive_experience_raw) over ()
        end as defensive_experience_z,
        case
            when stddev_samp(overall_star_power_raw) over () = 0 then 0
            else (overall_star_power_raw - avg(overall_star_power_raw) over ())
                / stddev_samp(overall_star_power_raw) over ()
        end as overall_star_power_z
    from raw_scores
)

select
    team_name,
    squad_status,
    source_player_count,
    squad_players,
    goalkeepers,
    defenders,
    midfielders,
    forwards,
    average_age,
    total_caps,
    total_goals,
    goalkeeper_caps,
    defender_caps,
    midfielder_caps,
    forward_caps,
    attacking_goals,
    defensive_caps,
    top_5_caps,
    top_5_goals,
    max_player_caps,
    max_player_goals,
    captain_caps,
    round(experience_score_raw, 3) as experience_score_raw,
    round(attacking_star_power_raw, 3) as attacking_star_power_raw,
    round(defensive_experience_raw, 3) as defensive_experience_raw,
    round(overall_star_power_raw, 3) as overall_star_power_raw,
    round(experience_score_z, 3) as experience_score_z,
    round(attacking_star_power_z, 3) as attacking_star_power_z,
    round(defensive_experience_z, 3) as defensive_experience_z,
    round(overall_star_power_z, 3) as overall_star_power_z
from scored
