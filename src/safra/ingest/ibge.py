"""Ingestao do IBGE: PAM (producao agricola municipal) e malhas (para o centroide).

Guarda o JSON/GeoJSON exatamente como veio da API, em particao por ano e UF. Nada
de parser no bronze: se o SIDRA mudar o formato, o arquivo antigo continua la e o
silver que quebra, nao a coleta.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .. import config
from ..net import fetch

SENTINELAS = {"-", "..", "...", "X", ""}


def caminho_pam(bronze: Path, ano: int, uf: int, nome: str = "soja") -> Path:
    return bronze / "ibge_pam" / f"ano={ano}" / f"uf={uf}" / f"{nome}.json"


def url_pam(ano: int, uf: int, nivel: str = "N6") -> str:
    variaveis = ",".join(str(v) for v in config.VARIAVEIS_PAM)
    # N3 = estado (todos os municipios somados pelo proprio SIDRA); N6 = municipio.
    localidade = f"N6[N3[{uf}]]" if nivel == "N6" else f"N3[{uf}]"
    return (
        f"{config.SIDRA}/{config.TABELA_PAM}/periodos/{ano}/variaveis/{variaveis}"
        f"?localidades={localidade}&classificacao=81[{config.PRODUTO_SOJA}]"
    )


def baixar_pam(anos: list[int], bronze: Path = config.BRONZE, uf: int = config.UF,
               force: bool = False) -> list[dict]:
    """PAM por municipio (`soja.json`) e o total do estado usado na reconciliacao."""
    coletas = []
    for ano in anos:
        coletas.append(fetch(url_pam(ano, uf), caminho_pam(bronze, ano, uf), force=force))
        coletas.append(
            fetch(url_pam(ano, uf, nivel="N3"), caminho_pam(bronze, ano, uf, "estado"),
                  force=force)
        )
    return coletas


def baixar_malhas(bronze: Path = config.BRONZE, uf: int = config.UF, force: bool = False) -> dict:
    url = (
        f"{config.MALHAS}/estados/{uf}?formato=application/vnd.geo+json"
        "&qualidade=intermediaria&intrarregiao=municipio"
    )
    destino = bronze / "malhas" / f"uf={uf}" / "municipios.geojson"
    coleta = fetch(url, destino, timeout=240, force=force)

    centroides = destino.with_name("centroides.csv")
    if force or not centroides.exists():
        escrever_centroides(destino, centroides)
    return coleta


def _anel_externo(geometria: dict) -> list[list[float]]:
    if geometria["type"] == "Polygon":
        return geometria["coordinates"][0]
    # MultiPolygon: fica com o maior anel, que em municipio do PR e o corpo principal.
    # Compara area em modulo: o anel pode vir em qualquer sentido (as malhas do IBGE
    # nao padronizam), e area assinada negativa escolheria o pedaco errado.
    aneis = [poligono[0] for poligono in geometria["coordinates"]]
    return max(aneis, key=lambda anel: abs(_area_assinada(anel)))


def _area_assinada(anel: list[list[float]]) -> float:
    area = 0.0
    for (x1, y1), (x2, y2) in zip(anel, anel[1:] + anel[:1], strict=False):
        area += x1 * y2 - x2 * y1
    return area / 2


def centroide(geometria: dict) -> tuple[float, float]:
    """Centroide de area (shoelace), nao media dos vertices: em poligono irregular
    a media de vertices cai fora do municipio e joga o pedido de clima no vizinho."""
    anel = _anel_externo(geometria)
    area = _area_assinada(anel)
    if abs(area) < 1e-12:
        lons = [p[0] for p in anel]
        lats = [p[1] for p in anel]
        return sum(lats) / len(lats), sum(lons) / len(lons)
    cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(anel, anel[1:] + anel[:1], strict=False):
        fator = x1 * y2 - x2 * y1
        cx += (x1 + x2) * fator
        cy += (y1 + y2) * fator
    if not math.isfinite(cx / (6 * area)):
        raise ValueError("centroide nao convergiu (geometria degenerada)")
    return cy / (6 * area), cx / (6 * area)


def escrever_centroides(geojson: Path, destino: Path) -> int:
    doc = json.loads(geojson.read_text(encoding="utf-8"))
    linhas = ["codigo_municipio,latitude,longitude"]
    for feature in doc["features"]:
        codigo = feature["properties"]["codarea"]
        lat, lon = centroide(feature["geometry"])
        linhas.append(f"{codigo},{lat:.6f},{lon:.6f}")
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return len(linhas) - 1
