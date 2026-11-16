-- Total do estado (nivel N3) na mesma safra. Serve de ancora: a soma dos municipios
-- tem que fechar com este numero, senao o recorte de municipios esta errado ou o
-- SIDRA revisou algum valor. E o check que mais pega erro de verdade.
create or replace table silver.pam_estado as
with arquivos as (
    select regexp_extract(filename, 'ano=(\d{4})', 1)::int as ano_colheita,
           content as texto
    from read_text('{bronze}/ibge_pam/ano=*/uf=*/estado.json')
),
variaveis as (
    select ano_colheita, unnest(cast(texto as JSON[])) as var
    from arquivos
),
resultados as (
    select ano_colheita,
           json_extract_string(var, '$.id') as variavel_id,
           unnest(cast(json_extract(var, '$.resultados') as JSON[])) as res
    from variaveis
),
series as (
    select ano_colheita,
           variavel_id,
           unnest(cast(json_extract(res, '$.series') as JSON[])) as serie
    from resultados
)
select
    ano_colheita,
    max(case when variavel_id = '109' then
        try_cast(json_extract_string(serie, '$.serie."' || ano_colheita || '"') as double)
    end) as area_plantada_ha,
    max(case when variavel_id = '214' then
        try_cast(json_extract_string(serie, '$.serie."' || ano_colheita || '"') as double)
    end) as producao_t,
    max(case when variavel_id = '112' then
        try_cast(json_extract_string(serie, '$.serie."' || ano_colheita || '"') as double)
    end) as rendimento_kg_ha
from series
group by ano_colheita;
