select
    count(*) as knockout_slot_count
from {{ ref('stg_knockout_slots') }}
having count(*) != 32
