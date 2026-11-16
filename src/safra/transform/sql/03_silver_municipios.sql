-- Centroides calculados na ingestao (a partir das malhas) + area plantada, que define
-- a ordem de prioridade dos pedidos de clima.
create or replace table silver.municipios as
select
    codigo_municipio,
    cast(latitude as double) as latitude,
    cast(longitude as double) as longitude
from read_csv('{bronze}/malhas/uf=*/centroides.csv', header = true,
              columns = {'codigo_municipio': 'VARCHAR', 'latitude': 'DOUBLE', 'longitude': 'DOUBLE'});

create or replace table silver.municipios_area as
with ultimo_ano as (
    select max(ano_colheita) as ano from silver.pam_soja
)
select
    m.codigo_municipio,
    m.latitude,
    m.longitude,
    p.municipio,
    p.area_plantada_ha
from silver.municipios m
left join silver.pam_soja p
       on p.codigo_municipio = m.codigo_municipio
      and p.ano_colheita = (select ano from ultimo_ano);
