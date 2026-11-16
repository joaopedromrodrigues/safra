-- Grao: municipio x safra, so com quem tem as duas pontas (PAM e clima).
-- A anomalia e medida contra a media do proprio municipio nas safras disponiveis:
-- isso tira solo, altitude e sistema de producao, que sao fixos, e deixa o desvio
-- do ano. E o modelo mais simples que nao vira "correlacao entre tecnologia e tempo".
create or replace table gold.fct_safra_municipio as
with juncao as (
    select
        p.ano_colheita,
        p.codigo_municipio,
        p.municipio,
        p.area_plantada_ha,
        p.area_colhida_ha,
        p.producao_t,
        p.rendimento_kg_ha,
        c.chuva_critica_mm,
        c.dias_criticos_com_chuva,
        c.veranico_critica_dias,
        c.tmax_critica_media_c,
        c.dias_tmax35_critica,
        c.gdd_critica,
        c.umidade_solo_critica,
        c.chuva_safra_mm,
        c.veranico_safra_dias,
        c.cobertura_janela,
        c.cobertura_critica
    from silver.pam_soja p
    join gold.clima_safra c
      on c.codigo_municipio = p.codigo_municipio
     and c.ano_colheita = p.ano_colheita
    where p.area_plantada_ha is not null
),
estatistica as (
    select
        *,
        avg(chuva_critica_mm) over (partition by codigo_municipio) as chuva_critica_media,
        stddev_samp(chuva_critica_mm) over (partition by codigo_municipio) as chuva_critica_desvio,
        avg(rendimento_kg_ha) over (partition by codigo_municipio) as rendimento_medio,
        stddev_samp(rendimento_kg_ha) over (partition by codigo_municipio) as rendimento_desvio,
        count(*) over (partition by codigo_municipio) as safras_no_municipio
    from juncao
)
select
    ano_colheita,
    codigo_municipio,
    municipio,
    area_plantada_ha,
    area_colhida_ha,
    producao_t,
    rendimento_kg_ha,
    chuva_critica_mm,
    dias_criticos_com_chuva,
    veranico_critica_dias,
    tmax_critica_media_c,
    dias_tmax35_critica,
    gdd_critica,
    umidade_solo_critica,
    chuva_safra_mm,
    veranico_safra_dias,
    cobertura_janela,
    cobertura_critica,
    safras_no_municipio,
    round(chuva_critica_media, 1) as chuva_critica_media,
    round(chuva_critica_mm - chuva_critica_media, 1) as chuva_anomalia_mm,
    case when chuva_critica_media > 0
         then round((chuva_critica_mm - chuva_critica_media) / chuva_critica_media, 4) end
        as chuva_anomalia_pct,
    case when chuva_critica_desvio > 0
         then round((chuva_critica_mm - chuva_critica_media) / chuva_critica_desvio, 3) end
        as chuva_anomalia_z,
    case when rendimento_medio > 0
         then round((rendimento_kg_ha - rendimento_medio) / rendimento_medio, 4) end
        as rendimento_anomalia_pct,
    case when rendimento_desvio > 0
         then round((rendimento_kg_ha - rendimento_medio) / rendimento_desvio, 3) end
        as rendimento_anomalia_z,
    case
        when chuva_critica_desvio is null or chuva_critica_desvio = 0 then 'sem_base'
        when (chuva_critica_mm - chuva_critica_media) / chuva_critica_desvio <= -1.5 then 'muito seco'
        when (chuva_critica_mm - chuva_critica_media) / chuva_critica_desvio <= -0.75 then 'seco'
        when (chuva_critica_mm - chuva_critica_media) / chuva_critica_desvio >= 1.5 then 'muito umido'
        when (chuva_critica_mm - chuva_critica_media) / chuva_critica_desvio >= 0.75 then 'umido'
        else 'normal'
    end as faixa_chuva
from estatistica;
