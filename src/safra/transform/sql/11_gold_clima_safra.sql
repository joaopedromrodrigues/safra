-- Features de clima por municipio x safra, em duas janelas.
--
-- A longa (set-abr) fica como contexto e para o check de cobertura. A que entra no
-- modelo e a critica (dez-jan): floracao e enchimento de grao. Veranico -- dias
-- consecutivos com menos de 1 mm -- sai de window function porque a media de chuva
-- esconde exatamente a sequencia que quebra a lavoura.
create or replace table gold.clima_safra as
with janela as (
    select
        codigo_municipio,
        data,
        chuva_mm,
        tmax_c,
        tmin_c,
        umidade_solo,
        case when month(data) >= 9 then year(data) + 1 else year(data) end as ano_colheita
    from silver.clima_diario
    where month(data) >= 9 or month(data) <= 4
),
-- veranico na safra inteira
grupo_safra as (
    select *, sum(case when coalesce(chuva_mm, 0) >= 1 then 1 else 0 end)
                  over (partition by codigo_municipio, ano_colheita order by data) as grupo
    from janela
),
veranico_safra as (
    select codigo_municipio, ano_colheita, max(tamanho) as veranico_safra_dias
    from (select codigo_municipio, ano_colheita, grupo, count(*) as tamanho
          from grupo_safra where coalesce(chuva_mm, 0) < 1
          group by 1, 2, 3)
    group by 1, 2
),
resumo_safra as (
    select codigo_municipio, ano_colheita,
           count(*) as dias_observados,
           sum(chuva_mm) as chuva_safra_mm
    from janela
    group by 1, 2
),
-- recorte dez-jan
critica as (
    select * from janela where month(data) in (12, 1)
),
grupo_critica as (
    select *, sum(case when coalesce(chuva_mm, 0) >= 1 then 1 else 0 end)
                  over (partition by codigo_municipio, ano_colheita order by data) as grupo
    from critica
),
veranico_critica as (
    select codigo_municipio, ano_colheita, max(tamanho) as veranico_critica_dias
    from (select codigo_municipio, ano_colheita, grupo, count(*) as tamanho
          from grupo_critica where coalesce(chuva_mm, 0) < 1
          group by 1, 2, 3)
    group by 1, 2
),
resumo_critica as (
    select codigo_municipio, ano_colheita,
           count(*) as dias_criticos,
           sum(chuva_mm) as chuva_critica_mm,
           count(chuva_mm) as dias_criticos_com_chuva,
           avg(tmax_c) as tmax_critica_media_c,
           sum(case when tmax_c > 35 then 1 else 0 end) as dias_tmax35_critica,
           avg(umidade_solo) as umidade_solo_critica,
           sum(greatest(0, least(30, (coalesce(tmax_c, tmin_c) + coalesce(tmin_c, tmax_c)) / 2) - 10))
               as gdd_critica
    from critica
    group by 1, 2
)
select
    s.codigo_municipio,
    s.ano_colheita,
    round(c.chuva_critica_mm, 1) as chuva_critica_mm,
    c.dias_criticos_com_chuva,
    vc.veranico_critica_dias,
    round(c.tmax_critica_media_c, 2) as tmax_critica_media_c,
    c.dias_tmax35_critica,
    round(c.umidade_solo_critica, 3) as umidade_solo_critica,
    round(c.gdd_critica, 1) as gdd_critica,
    round(s.chuva_safra_mm, 1) as chuva_safra_mm,
    v.veranico_safra_dias,
    s.dias_observados,
    d.dias_esperados,
    round(s.dias_observados::double / d.dias_esperados, 4) as cobertura_janela,
    round(c.dias_criticos::double / 62, 4) as cobertura_critica
from resumo_critica c
join resumo_safra s using (codigo_municipio, ano_colheita)
left join veranico_critica vc using (codigo_municipio, ano_colheita)
join gold.dim_safra d using (ano_colheita)
left join veranico_safra v using (codigo_municipio, ano_colheita);
