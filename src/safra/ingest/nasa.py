"""Ingestao de clima diario do NASA POWER, um pedido por municipio.

O POWER devolve um CSV com um bloco de cabecalho de tamanho variavel (depende dos
parametros pedidos) antes da linha `YEAR,DOY,...`. Guardamos o CSV sem esse bloco
e o cabecalho cru num `meta.json` ao lado, para nao deixar o silver dependente de
um `skip=N` que muda quando alguem acrescenta um parametro.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import config
from ..net import fetch

CABECALHO = ["YEAR", "DOY", *config.POWER_PARAMS]
FILL = -999.0


def url_power(lat: float, lon: float, inicio: str, fim: str) -> str:
    params = ",".join(config.POWER_PARAMS)
    return (
        f"{config.POWER}?parameters={params}&community=AG"
        f"&latitude={lat:.4f}&longitude={lon:.4f}"
        f"&start={inicio}&end={fim}&format=CSV"
    )


def caminho_clima(bronze: Path, codigo: str) -> Path:
    return bronze / "nasa_power" / f"municipio={codigo}" / "clima.csv"


def separar_bloco(texto: str) -> tuple[list[str], list[str]]:
    """Devolve (cabecalho_de_metadados, linhas_de_dados_a_partir_do_header)."""
    linhas = texto.replace("\r\n", "\n").split("\n")
    for indice, linha in enumerate(linhas):
        if linha.strip().upper().startswith("YEAR,DOY"):
            return linhas[:indice], linhas[indice:]
    raise ValueError("CSV do POWER sem linha de cabecalho YEAR,DOY")


def normalizar(texto: str) -> tuple[str, dict]:
    """Tira o bloco de metadados e troca o preenchimento -999 por vazio."""
    meta, dados = separar_bloco(texto)
    corpo = []
    for linha in dados:
        if not linha.strip():
            continue
        campos = linha.split(",")
        campos = ["" if campo.strip() in ("", str(int(FILL))) else campo for campo in campos]
        corpo.append(",".join(campos))
    assert corpo[0].upper().startswith("YEAR,DOY"), corpo[0]
    return "\n".join(corpo) + "\n", {"bloco_metadados": meta}


def baixar_clima(municipios: list[dict], bronze: Path = config.BRONZE,
                 force: bool = False) -> list[dict]:
    inicio, fim = config.periodo_power()
    coletas = []
    for municipio in municipios:
        codigo = str(municipio["codigo_municipio"])
        destino = caminho_clima(bronze, codigo)
        url = url_power(float(municipio["latitude"]), float(municipio["longitude"]), inicio, fim)

        if destino.exists() and not force:
            coletas.append({"destino": str(destino), "status": "cache", "url": url})
            continue

        bruto = destino.with_name("clima.bruto.csv")
        coleta = fetch(url, bruto, timeout=300, min_intervalo=1.5, force=force)
        texto = bruto.read_text(encoding="utf-8")
        limpo, meta = normalizar(texto)
        destino.write_text(limpo, encoding="utf-8")
        destino.with_name("meta.json").write_text(
            json.dumps({"codigo_municipio": codigo, "url": url, **meta}, ensure_ascii=False,
                       indent=2),
            encoding="utf-8",
        )
        coletas.append({**coleta, "destino": str(destino), "status": "baixado"})
    return coletas


def ler_clima(caminho: Path) -> list[dict]:
    """Le um clima.csv normalizado -> lista de dicts com data e valores (None no fill)."""
    import csv
    from datetime import date, timedelta

    registros = []
    with caminho.open(newline="", encoding="utf-8") as fh:
        for linha in csv.DictReader(fh):
            dia = date(int(linha["YEAR"]), 1, 1) + timedelta(days=int(linha["DOY"]) - 1)
            registro: dict[str, object] = {"data": dia}
            for nome in config.POWER_PARAMS:
                bruto = (linha.get(nome) or "").strip()
                registro[nome] = float(bruto) if bruto else None
            registros.append(registro)
    return registros
