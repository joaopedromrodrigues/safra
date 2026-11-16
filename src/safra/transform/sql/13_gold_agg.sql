-- Serie do estado: as medias do PR ponderadas pela area de cada municipio.
-- Ponderar importa porque o recorte nao e o estado inteiro -- municipio pequeno nao
-- pode pesar igual a Cascavel na media do Parana.
create or replace table gold.agg_safra_estado as
select
    ano_colheita,
    count(*) as municipios,
    sum(area_plantada_ha) as area_plantada_ha,
    sum(area_colhida_ha) as area_colhida_ha,
    sum(producao_t) as producao_t,
    round(sum(producao_t) * 1000 / nullif(sum(area_colhida_ha), 0), 1) as rendimento_kg_ha,
    round(sum(chuva_critica_mm * area_plantada_ha) / nullif(sum(area_plantada_ha), 0), 1)
        as chuva_critica_ponderada_mm,
    round(sum(chuva_anomalia_pct * area_plantada_ha) / nullif(sum(area_plantada_ha), 0), 4)
        as chuva_anomalia_pct_ponderada,
    round(sum(veranico_critica_dias * area_plantada_ha) / nullif(sum(area_plantada_ha), 0), 1)
        as veranico_critica_ponderado_dias,
    round(sum(case when faixa_chuva in ('muito seco', 'seco') then 1 else 0 end) * 1.0
          / count(*), 3) as pct_municipios_secos,
    round(min(cobertura_janela), 3) as cobertura_janela_minima
from gold.fct_safra_municipio
group by 1
order by 1;

-- Ponte com o numero oficial do estado, para enxergar o quanto o recorte de municipios
-- representa do PR em cada safra.
create or replace table gold.reconciliacao_safra as
select
    e.ano_colheita,
    e.area_plantada_ha as area_estado_ibge,
    s.area_plantada_ha as area_coberta,
    round(s.area_plantada_ha / nullif(e.area_plantada_ha, 0), 4) as cobertura_area,
    e.producao_t as producao_estado_ibge,
    s.producao_t as producao_coberta,
    round(s.producao_t / nullif(e.producao_t, 0), 4) as cobertura_producao,
    e.rendimento_kg_ha as rendimento_estado_ibge,
    s.rendimento_kg_ha as rendimento_municipios
from silver.pam_estado e
join gold.agg_safra_estado s using (ano_colheita);
