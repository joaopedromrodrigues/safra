create schema if not exists gold;

create or replace table gold.dim_municipio as
select
    m.codigo_municipio,
    coalesce(m.municipio, 'municipio ' || m.codigo_municipio) as municipio,
    m.latitude,
    m.longitude,
    m.area_plantada_ha,
    rank() over (order by m.area_plantada_ha desc nulls last) as ranking_area_estado,
    exists (select 1 from silver.clima_diario c where c.codigo_municipio = m.codigo_municipio)
        as tem_clima
from silver.municipios_area m;

create or replace table gold.dim_safra as
with safras as (select distinct ano_colheita from silver.pam_soja)
select
    ano_colheita,
    (ano_colheita - 1) || '/' || right(ano_colheita::varchar, 2) as safra,
    make_date(ano_colheita - 1, 9, 1) as janela_inicio,
    make_date(ano_colheita, 4, 30) as janela_fim,
    date_diff('day', make_date(ano_colheita - 1, 9, 1), make_date(ano_colheita, 4, 30)) + 1
        as dias_esperados
from safras;
