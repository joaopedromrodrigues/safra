"""Checagens de qualidade que rodam depois do gold.

Escolhi seis regras que quebram de verdade neste pipeline (grao duplicado, numero
fora de faixa, janela de clima incompleta, recorte de municipio que nao fecha com
o oficial) em vez de um catalogo generico. Cada uma devolve o valor medido e o
limite, para o log dizer o numero e nao so "falhou".
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb

from .. import config


@dataclass
class Resultado:
    nome: str
    medido: float | int | str
    limite: str
    passou: bool
    detalhe: str = ""


def _escalar(con: duckdb.DuckDBPyConnection, sql: str):
    return con.execute(sql).fetchone()[0]


def _numerico(valor, casas: int = 4):
    return "sem_dados" if valor is None else round(float(valor), casas)


def rodar(con: duckdb.DuckDBPyConnection) -> list[Resultado]:
    resultados: list[Resultado] = []

    duplicados = _escalar(con, """
        select count(*) from (
            select codigo_municipio, ano_colheita, count(*) as n
            from gold.fct_safra_municipio group by 1, 2 having count(*) > 1
        )
    """)
    resultados.append(Resultado("grao_unico", duplicados, "== 0", duplicados == 0,
                                "municipio x safra nao pode repetir no fato"))

    rendimento = con.execute("""
        select min(rendimento_kg_ha), max(rendimento_kg_ha) from gold.fct_safra_municipio
    """).fetchone()
    ok = rendimento[0] is not None and 300 <= rendimento[0] and rendimento[1] <= 6000
    resultados.append(Resultado("rendimento_na_faixa", f"{rendimento[0]:.0f}-{rendimento[1]:.0f}",
                                "300-6000 kg/ha", ok, "fora disso e erro de unidade no SIDRA"))

    chuva = con.execute("""
        select min(chuva_critica_mm), max(chuva_critica_mm) from gold.fct_safra_municipio
    """).fetchone()
    ok = chuva[0] is not None and 50 <= chuva[0] and chuva[1] <= 1500
    resultados.append(Resultado("chuva_na_faixa", f"{chuva[0]:.0f}-{chuva[1]:.0f} mm",
                                "50-1500 mm em dez-jan", ok, "POWER em mm/dia"))

    cobertura = _escalar(con, "select min(cobertura_area) from gold.reconciliacao_safra")
    resultados.append(Resultado("cobertura_area", _numerico(cobertura), ">= 0.80",
                                cobertura is not None and cobertura >= 0.80,
                                "fracao da area plantada do PR presente no recorte"))

    # Producao coberta x area coberta: se o recorte fosse viesado (so municipio grande,
    # so municipio de alta produtividade), estas duas razoes se separariam.
    vies = _escalar(con, """
        select max(abs(cobertura_producao - cobertura_area)) from gold.reconciliacao_safra
    """)
    resultados.append(Resultado("recorte_sem_vies", _numerico(vies), "<= 0.10",
                                vies is not None and vies <= 0.10,
                                "|producao coberta - area coberta|: recorte nao pode ser viesado"))

    janela = _escalar(con, "select min(cobertura_janela) from gold.fct_safra_municipio")
    resultados.append(Resultado("janela_clima_completa", _numerico(janela), ">= 0.98",
                                janela is not None and janela >= 0.98,
                                "dias com dado / dias da janela set-abr"))

    return resultados


def resumo(resultados: list[Resultado]) -> dict:
    return {
        "ok": all(r.passou for r in resultados),
        "checks": [asdict(r) for r in resultados],
    }


def salvar(resultados: list[Resultado], destino: Path | None = None) -> Path:
    destino = destino or (config.DIST / "quality.json")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resumo(resultados), ensure_ascii=False, indent=2),
                       encoding="utf-8")
    return destino
