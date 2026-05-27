with source as (
    select *
    from read_csv_auto(
        '{{ var("raw_data_path") }}/knockout_slots.csv',
        header = true,
        normalize_names = true
    )
)

select
    cast(match_id as varchar) as match_id,
    trim(cast(round as varchar)) as round_name,
    cast(multiplier as double) as score_multiplier,
    try_cast(date_utc as timestamp) as match_date_utc,
    trim(cast(venue as varchar)) as venue,
    trim(cast(slot_home as varchar)) as slot_home,
    trim(cast(slot_away as varchar)) as slot_away
from source
