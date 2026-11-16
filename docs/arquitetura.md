# Architecture

```
SIDRA API (IBGE)          Malhas API (IBGE)          NASA POWER API
 PAM tabela 1612           geometria municipal         serie diaria por ponto
 municipio x ano           (uma chamada, 399 feitos)   (~1 pedido por municipio)
       |                          |                            |
       v                          v                            v
 bronze/ibge_pam/           bronze/malhas/               bronze/nasa_power/
   ano=YYYY/uf=41/            uf=41/municipios.geojson     municipio=NNNNNNN/
     soja.json                  uf=41/centroides.csv          clima.csv
     estado.json                                              meta.json
       |                          |                            |
       +--------------------------+----------------------------+
                                  |
                          DuckDB (engine local)
                                  |
              silver.pam_soja  silver.pam_estado  silver.municipios
              silver.clima_diario  silver.clima_cobertura
                                  |
                       gold.dim_municipio / dim_safra
                       gold.clima_safra   (features dez-jan + safra inteira)
                       gold.fct_safra_municipio   (grao: municipio x safra)
                       gold.agg_safra_estado / reconciliacao_safra
                                  |
                    quality checks -> dist/quality.json
                    export -> dist/*.csv  +  docs/figuras/*.png
```

## Layer contract

| Layer | Storage | Contract |
|---|---|---|
| bronze | files exactly as the APIs return them | never edited after write; every fetch logged in `data/_manifest.jsonl` with url, sha256, bytes, timestamp |
| silver | DuckDB tables built by SQL | typed, deduplicated, sentinels (`-`, `..`, `...`) kept as text next to the parsed value so suppression can be counted |
| gold | DuckDB tables built by SQL | one fact table, dimensional grain, anomalies measured inside each municipality |
| dist | CSV + PNG | what a reader or a downstream tool consumes; regenerated on every run |

## Why this shape

* **Files first, engine second.** The bronze layout is `prefix/<entity>/<partition>/<file>`,
  which is what S3 + Athena needs. Swapping DuckDB for Athena/Glue is a matter of pointing
  `read_text`/`read_csv` at `s3://` and changing the catalog — the SQL keeps the partition
  columns (`ano=`, `uf=`, `municipio=`) it filters on.
* **Rebuildable warehouse.** Deleting `data/safra.duckdb` costs 4 seconds of compute and zero
  API calls, because bronze is on disk. Anything that takes 10 minutes of download is the only
  irreplaceable part, so it is written once and never recomputed.
* **Idempotent by construction.** Every `create or replace table` reads bronze and writes a
  full table. A run that dies in the middle leaves the previous warehouse intact.
* **One request per municipality, cached.** NASA POWER's per-point API is the bottleneck
  (~1.5 s per call, throttled to stay polite). The 170 requests needed for 80% of the state's
  area are the difference between a 8-minute first run and a 30-minute one for all 399
  municipalities — see `docs/decisoes.md`.
* **Orchestration is separate from logic.** `src/safra/pipeline.py` holds one function per
  stage; `dags/safra_dag.py` and `cli.py` only wire them.

## Scheduling

Annual source, revised climatology: the DAG runs monthly (`0 6 1 2 *`), and the February run
is the one that matters because it closes the December–January window of the last two harvests.
Retries have exponential backoff because POWER answers `429` when a burst of requests arrives.

## What is not here

No partitioning of the fact table by year (1.5k rows do not need it), no incremental merge
(the PAM revisits past years, so a full rebuild is correct and cheaper to reason about), no
secret handling (all three sources are public and keyless).
