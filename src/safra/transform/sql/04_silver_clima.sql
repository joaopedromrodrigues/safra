-- Clima diario do POWER: YEAR/DOY -> data, e as colunas com nome do projeto.
-- O -999 (fill) ja saiu na ingestao; aqui so falta nao confundir ausencia com zero.
create or replace table silver.clima_diario as
with bruto as (
    select
        regexp_extract(filename, 'municipio=(\d+)', 1) as codigo_municipio,
        * exclude (filename)
    from read_csv('{bronze}/nasa_power/municipio=*/clima.csv',
                  header = true, filename = true, union_by_name = true,
                  columns = {'YEAR': 'INTEGER', 'DOY': 'INTEGER',
                             'PRECTOTCORR': 'DOUBLE', 'T2M_MAX': 'DOUBLE',
                             'T2M_MIN': 'DOUBLE', 'RH2M': 'DOUBLE', 'GWETROOT': 'DOUBLE'})
)
select
    codigo_municipio,
    make_date(YEAR, 1, 1) + (DOY - 1) as data,
    PRECTOTCORR as chuva_mm,
    T2M_MAX as tmax_c,
    T2M_MIN as tmin_c,
    RH2M as umidade_rel_pct,
    GWETROOT as umidade_solo
from bruto;

-- Quanto de cada janela de safra veio vazio. Fica em tabela propria porque e o tipo de
-- coisa que precisa estar visivel no numero final, e nao escondida num `where not null`.
create or replace table silver.clima_cobertura as
select
    codigo_municipio,
    case when month(data) >= 9 then year(data) + 1 else year(data) end as ano_colheita,
    count(*) as dias_presentes,
    count(chuva_mm) as dias_com_chuva
from silver.clima_diario
where month(data) >= 9 or month(data) <= 4
group by 1, 2;
