with group_stage as (
    select
        match_id,
        'group' as competition_phase,
        group_letter,
        cast(null as varchar) as round_name,
        cast(1 as double) as score_multiplier,
        home_team,
        away_team,
        match_date_utc,
        venue,
        false as uses_slot_labels
    from {{ ref('stg_group_fixtures') }}
),

knockout_stage as (
    select
        match_id,
        'knockout' as competition_phase,
        cast(null as varchar) as group_letter,
        round_name,
        score_multiplier,
        slot_home as home_team,
        slot_away as away_team,
        match_date_utc,
        venue,
        true as uses_slot_labels
    from {{ ref('stg_knockout_slots') }}
)

select * from group_stage
union all
select * from knockout_stage
