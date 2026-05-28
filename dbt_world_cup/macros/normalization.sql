{% macro canonical_team_name(column_name) -%}
    case
        when lower(trim(strip_accents(cast({{ column_name }} as varchar)))) in ('usa', 'united states') then 'United States'
        when lower(trim(strip_accents(cast({{ column_name }} as varchar)))) in ('bosnia-herzegovina', 'bosnia and herzegovina') then 'Bosnia and Herzegovina'
        when lower(trim(strip_accents(cast({{ column_name }} as varchar)))) in ('cabo verde', 'cape verde', 'cape verde islands') then 'Cape Verde'
        when lower(trim(strip_accents(cast({{ column_name }} as varchar)))) in ('cote d''ivoire', 'cote divoire', 'ivory coast') then 'Ivory Coast'
        when lower(trim(strip_accents(cast({{ column_name }} as varchar)))) in ('czechia', 'czech republic') then 'Czech Republic'
        when lower(trim(strip_accents(cast({{ column_name }} as varchar)))) in ('turkiye', 'turkey') then 'Turkey'
        when lower(trim(strip_accents(cast({{ column_name }} as varchar)))) in ('congo dr', 'dr congo', 'democratic republic of congo') then 'DR Congo'
        when lower(trim(strip_accents(cast({{ column_name }} as varchar)))) in ('south korea', 'korea republic') then 'South Korea'
        when lower(trim(strip_accents(cast({{ column_name }} as varchar)))) in ('curacao') then 'Curaçao'
        when lower(trim(strip_accents(cast({{ column_name }} as varchar)))) in ('iran', 'ir iran') then 'Iran'
        else trim(cast({{ column_name }} as varchar))
    end
{%- endmacro %}


{% macro normalized_name_key(column_name) -%}
    trim(regexp_replace(lower(strip_accents(cast({{ column_name }} as varchar))), '[^a-z0-9]+', ' ', 'g'))
{%- endmacro %}
