"""Caminhos e parametros do projeto.

Tudo que muda entre execucao local, teste e Airflow fica aqui. O default assume
que o repositorio e a raiz (make demo, pytest); a DAG do Airflow passa SAFRA_HOME.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from datetime import date
from pathlib import Path

HOME = Path(os.environ.get("SAFRA_HOME", Path.cwd())).resolve()
DATA = HOME / "data"
BRONZE = DATA / "bronze"
SILVER = DATA / "silver"
GOLD = DATA / "gold"
DIST = HOME / "dist"
DB_PATH = DATA / "safra.duckdb"
MANIFEST = DATA / "_manifest.jsonl"

# Mesorregiao/municipio do Parana, soja em grao na PAM (tabela 1612, classe 81/2713).
UF = 41
TABELA_PAM = 1612
PRODUTO_SOJA = 2713
VARIAVEIS_PAM = (109, 112, 214, 216)  # area plantada, rendimento, producao, area colhida

# Safra agricola brasileira da soja: setembro do ano anterior ate abril do ano da colheita.
SAFRA_MES_INICIO = 9
SAFRA_MES_FIM = 4

PRIMEIRO_ANO = 2016
ULTIMO_ANO = 2024

# Centroide e resolucao de 0.5 grau do POWER: a chuva e a mesma celula para
# municipios vizinhos, o que borra o sinal em cidades pequenas (ver docs/decisoes.md).
POWER_PARAMS = ("PRECTOTCORR", "T2M_MAX", "T2M_MIN", "RH2M", "GWETROOT")

SIDRA = "https://servicodados.ibge.gov.br/api/v3/agregados"
MALHAS = "https://servicodados.ibge.gov.br/api/v3/malhas"
POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"

USER_AGENT = "safra/0.1 (portfolio; contato: joaomatiasrodrigues@gmail.com)"


def anos(intervalo: str | Sequence[int] | None = None) -> list[int]:
    """Aceita '2016-2024', '2020', uma lista, ou nada (default do projeto)."""
    if intervalo is None:
        return list(range(PRIMEIRO_ANO, ULTIMO_ANO + 1))
    if not isinstance(intervalo, str):
        return sorted(intervalo)
    if "-" in intervalo:
        inicio, fim = intervalo.split("-", 1)
        return list(range(int(inicio), int(fim) + 1))
    return [int(intervalo)]


def janela_safra(ano_colheita: int) -> tuple[date, date]:
    inicio = date(ano_colheita - 1, SAFRA_MES_INICIO, 1)
    fim_mes = SAFRA_MES_FIM
    proximo = date(ano_colheita, fim_mes + 1, 1) if fim_mes < 12 else date(ano_colheita + 1, 1, 1)
    return inicio, date.fromordinal(proximo.toordinal() - 1)


def rotulo_safra(ano_colheita: int) -> str:
    return f"{ano_colheita - 1}/{str(ano_colheita)[-2:]}"


def periodo_power() -> tuple[str, str]:
    """Recorte pedido ao POWER: cobre a janela de todas as safras do projeto."""
    primeiro, _ = janela_safra(min(anos()))
    _, ultimo = janela_safra(max(anos()))
    return primeiro.strftime("%Y%m%d"), ultimo.strftime("%Y%m%d")


# Janela critica: na soja do PR a floracao e o enchimento de grao caem em dez-jan.
# E ali que o veranico quebra safra. O acumulado de set-abr nao correlaciona com
# rendimento (r=-0.07); o veranico de dez-jan correlaciona (r=-0.58). Ver docs/decisoes.md.
CRITICA_MES_INICIO = 12
CRITICA_MES_FIM = 1
CRITICA_DIAS = 31 + 31
