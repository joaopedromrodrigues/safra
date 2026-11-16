"""Monta silver e gold no DuckDB a partir do bronze em arquivo.

Cada passo e um arquivo .sql em src/safra/sql, executado em ordem alfabetica. O
banco e descartavel: apagar data/safra.duckdb e rodar de novo reconstroi tudo a
partir do bronze, que e a unica coisa que nao se pode perder. E o mesmo desenho
que o pipeline da empresa usa em S3 + Athena, so que com engine local -- por isso
o SQL le caminho de particao (`ano=*/uf=*`) em vez de tabela carregada.
"""

from __future__ import annotations

import time
from pathlib import Path

import duckdb

from .. import config

SQL_DIR = Path(__file__).parent / "sql"


def conectar(caminho: Path = config.DB_PATH, threads: int = 4) -> duckdb.DuckDBPyConnection:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(caminho))
    con.execute(f"PRAGMA threads={threads}")
    con.execute("PRAGMA preserve_insertion_order=false")
    return con


def arquivos_sql(padrao: str = "*.sql") -> list[Path]:
    return sorted(SQL_DIR.glob(padrao))


def executar(con: duckdb.DuckDBPyConnection, caminho: Path) -> float:
    sql = caminho.read_text(encoding="utf-8").replace("{bronze}", str(config.BRONZE))
    inicio = time.monotonic()
    con.execute(sql)
    return round(time.monotonic() - inicio, 2)


def rodar(con: duckdb.DuckDBPyConnection, padrao: str = "*.sql") -> list[tuple[str, float]]:
    tempos = []
    for caminho in arquivos_sql(padrao):
        tempos.append((caminho.name, executar(con, caminho)))
    return tempos


def tabela(con: duckdb.DuckDBPyConnection, query: str):
    """Atalho para trazer resultado como DataFrame."""
    return con.execute(query).fetch_df()


def contagem(con: duckdb.DuckDBPyConnection, tabela: str) -> int:
    return con.execute(f"select count(*) from {tabela}").fetchone()[0]


def municipios_por_area(
    con: duckdb.DuckDBPyConnection,
    quantos: int | None = None,
    cobertura: float | None = None,
) -> list[dict]:
    """Municipios que interessam ao POWER, por area plantada de soja.

    O POWER responde um pedido por municipio e leva ~1,5 s cada. Em vez de pegar os
    398 e esperar, o padrao do projeto e o conjunto que cobre uma fracao da area
    plantada do estado (calculo de Pareto sobre a propria PAM). `quantos` forca um
    numero fixo; `quantos=None` sem `cobertura` pega todos.
    """
    base = """
        with ultimo as (select max(ano_colheita) as ano from silver.pam_soja),
        total as (
            select area_plantada_ha as ha from silver.pam_estado
            where ano_colheita = (select ano from ultimo)
        ),
        ranque as (
            select m.codigo_municipio, m.latitude, m.longitude, m.area_plantada_ha,
                   (sum(m.area_plantada_ha) over (
                        order by m.area_plantada_ha desc, m.codigo_municipio) - m.area_plantada_ha)
                       / (select ha from total) as acumulado_anterior,
                   sum(m.area_plantada_ha) over (
                        order by m.area_plantada_ha desc, m.codigo_municipio)
                       / (select ha from total) as acumulado
            from silver.municipios_area m
            where m.area_plantada_ha is not null and m.latitude is not null
        )
        select codigo_municipio, latitude, longitude, area_plantada_ha, acumulado,
               acumulado_anterior
        from ranque
    """
    if quantos is not None:
        linhas = con.execute(
            f"select * from ({base}) order by area_plantada_ha desc limit {int(quantos)}"
        ).fetchall()
    elif cobertura is not None:
        # acumulado_anterior < alvo inclui o municipio que cruza o limite
        linhas = con.execute(
            f"select * from ({base}) where acumulado_anterior < {float(cobertura):.4f} "
            "order by area_plantada_ha desc"
        ).fetchall()
    else:
        linhas = con.execute(f"select * from ({base}) order by area_plantada_ha desc").fetchall()
    return [
        {"codigo_municipio": r[0], "latitude": r[1], "longitude": r[2],
         "area_plantada_ha": r[3], "cobertura_acumulada": r[4]}
        for r in linhas
    ]
