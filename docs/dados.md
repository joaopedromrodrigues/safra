# Data dictionary and sources

## Sources

| Source | What | Grain | Access |
|---|---|---|---|
| IBGE — PAM, table 1612 | planted area, harvested area, production, average yield of temporary crops | municipality × harvest year × crop | public, no key, `servicodados.ibge.gov.br` |
| IBGE — Malhas | municipal polygons of Paraná | municipality | public, no key, one call per state |
| NASA POWER (`community=AG`) | daily rainfall, max/min temperature, relative humidity, root-zone soil wetness | point (0.5°) × day | public, no key, one call per point |

Crop filter: class 81 / category 2713 (soybean). Years: configurable, default 2016–2024 harvest
years. Each Parana harvest year `Y` is the window 1 Sep `Y-1` → 30 Apr `Y`.

## Gold tables

### `dim_municipio`
| column | type | meaning |
|---|---|---|
| codigo_municipio | VARCHAR | 7-digit IBGE code, joins every other table |
| municipio | VARCHAR | name as published by the PAM |
| latitude, longitude | DOUBLE | area centroid of the municipal polygon |
| area_plantada_ha | DOUBLE | soybean area in the most recent harvest year available |
| ranking_area_estado | BIGINT | position in the state ranking by soybean area |
| tem_clima | BOOLEAN | whether the POWER download was done for this municipality |

### `dim_safra`
| column | type | meaning |
|---|---|---|
| ano_colheita | INTEGER | harvest year (`2022` = season 2021/22) |
| safra | VARCHAR | label `2021/22` |
| janela_inicio, janela_fim | DATE | 1 Sep → 30 Apr |
| dias_esperados | INTEGER | days in the long window (243) |

### `clima_safra`
| column | type | meaning |
|---|---|---|
| codigo_municipio, ano_colheita | | grain |
| chuva_critica_mm | DOUBLE | rainfall sum, 1 Dec → 31 Jan |
| veranico_critica_dias | BIGINT | longest run of consecutive days with < 1 mm in Dec–Jan |
| dias_criticos_com_chuva | BIGINT | days in Dec–Jan with a non-null rainfall value |
| tmax_critica_media_c | DOUBLE | mean daily max temperature, Dec–Jan |
| dias_tmax35_critica | BIGINT | days above 35 °C, Dec–Jan |
| gdd_critica | DOUBLE | growing degree days (base 10 °C, capped at 30 °C), Dec–Jan |
| umidade_solo_critica | DOUBLE | mean root-zone wetness fraction (0–1), Dec–Jan |
| chuva_safra_mm | DOUBLE | rainfall sum, 1 Sep → 30 Apr |
| veranico_safra_dias | BIGINT | longest dry run in the long window |
| dias_observados, dias_esperados | INTEGER | completeness of the long window |
| cobertura_janela, cobertura_critica | DOUBLE | observed / expected days, per window |

### `fct_safra_municipio`
Grain: `codigo_municipio` × `ano_colheita`. Carries everything from `clima_safra` plus the PAM
measures and the deviation columns:

| column | type | meaning |
|---|---|---|
| area_plantada_ha, area_colhida_ha | DOUBLE | PAM, hectares |
| producao_t | DOUBLE | PAM, tonnes |
| rendimento_kg_ha | DOUBLE | PAM, kg/ha |
| chuva_critica_media | DOUBLE | mean of `chuva_critica_mm` for this municipality across seasons |
| chuva_anomalia_mm / _pct / _z | DOUBLE | deviation from that mean, absolute / relative / in standard deviations |
| rendimento_anomalia_pct / _z | DOUBLE | same idea for yield |
| faixa_chuva | VARCHAR | `muito seco`, `seco`, `normal`, `umido`, `muito umido`, `sem_base` (z-score bands of ±0.75 / ±1.5) |
| safras_no_municipio | BIGINT | how many seasons the municipality has; the anomaly needs ≥ 5 to be meaningful |

### `agg_safra_estado`
One row per harvest year, weighted by planted area: total and mean yield, rainfall anomaly,
mean dry spell, and the share of municipalities in the two driest bands.

### `reconciliacao_safra`
One row per harvest year comparing the municipality cut with the official state total:
`cobertura_area`, `cobertura_producao`, and both yield series. This is the table the
`cobertura_area` and `reconcilia_producao` checks read.

## Known limits

* POWER is a 0.5° reanalysis grid. Neighbouring municipalities often share the same cell, so
  the climate feature is not municipal — it is "the cell that contains the municipal centroid".
* The PAM revises published values; a rebuild from bronze therefore changes history. Bronze
  keeps every payload ever downloaded, but the current silver only reads the latest file per
  partition (no temporal versioning — that would be a `valid_from` column, not a folder).
* Rainfall below 1 mm/day is treated as dry. POWER's daily product is a spatial average, so a
  local shower that wets 30% of a municipality shows as ~0.3 mm and counts as a dry day.
