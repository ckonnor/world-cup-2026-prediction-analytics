select 1
where (select count(*) from {{ ref('bi_team_profiles') }}) != 48
