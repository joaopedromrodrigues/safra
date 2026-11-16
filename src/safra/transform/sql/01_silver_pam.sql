-- PAM: do JSON cru do SIDRA para uma tabela longa (celula = municipio x ano x variavel).
-- O SIDRA usa "-" (sem lavoura), ".." (nao aplicavel) e "..." (nao disponivel) no mesmo
-- campo numerico. Guardamos o texto original e a conversao, para poder contar quanto
-- dado foi suprimido em vez de so jogar NULL e seguir.
create schema if not exists silver;

create or replace table silver.pam_celulas as
with arquivos as (
    select regexp_extract(filename, 'ano=(\d{4})', 1)::int as ano_colheita,
           content as texto
    from read_text('{bronze}/ibge_pam/ano=*/uf=*/soja.json')
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
),
valores as (
    select ano_colheita,
           variavel_id,
           json_extract_string(serie, '$.localidade.id') as codigo_municipio,
           split_part(json_extract_string(serie, '$.localidade.nome'), ' - ', 1) as municipio,
           nullif(trim(json_extract_string(serie, '$.serie."' || ano_colheita || '"')), '')
               as valor_bruto
    from series
)
select
    ano_colheita,
    codigo_municipio,
    municipio,
    case variavel_id
        when '109' then 'area_plantada_ha'
        when '216' then 'area_colhida_ha'
        when '214' then 'producao_t'
        when '112' then 'rendimento_kg_ha'
    end as variavel,
    valor_bruto,
    try_cast(valor_bruto as double) as valor,
    valor_bruto is not null
        and try_cast(valor_bruto as double) is null as suprimido
from valores;

-- Visao larga, que e como o resto do warehouse consome.
create or replace table silver.pam_soja as
select
    ano_colheita,
    codigo_municipio,
    municipio,
    max(valor) filter (where variavel = 'area_plantada_ha') as area_plantada_ha,
    max(valor) filter (where variavel = 'area_colhida_ha') as area_colhida_ha,
    max(valor) filter (where variavel = 'producao_t') as producao_t,
    max(valor) filter (where variavel = 'rendimento_kg_ha') as rendimento_kg_ha
from silver.pam_celulas
group by 1, 2, 3;
