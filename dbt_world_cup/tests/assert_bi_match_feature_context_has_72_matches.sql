select 1
where (select count(*) from {{ ref('bi_match_feature_context') }}) != 72
