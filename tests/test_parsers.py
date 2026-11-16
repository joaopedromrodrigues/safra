"""Parsers: os tres formatos que o projeto tem que aguentar.

Cada um ja quebrou uma vez durante o desenvolvimento -- JSON aninhado do SIDRA,
bloco de metadados variavel do POWER, geometria MultiPolygon nas malhas.
"""

import pytest

from safra.ingest import ibge, nasa

CSV_POWER = """-BEGIN HEADER-
NASA/POWER Source Native Resolution Daily Data
-END HEADER-
YEAR,DOY,PRECTOTCORR,T2M_MAX,T2M_MIN,RH2M,GWETROOT
2022,1,0.5,30.1,21.0,80.0,-999
2022,2,0.0,29.8,20.5,82.1,0.41
"""


def test_normalizar_tira_metadados_e_zera_fill():
    limpo, meta = nasa.normalizar(CSV_POWER)
    linhas = limpo.strip().splitlines()
    assert linhas[0].startswith("YEAR,DOY")
    assert linhas[1] == "2022,1,0.5,30.1,21.0,80.0,"
    assert linhas[2].endswith("0.41")
    assert meta["bloco_metadados"][0] == "-BEGIN HEADER-"


def test_csv_sem_bloco_de_dados_estoura():
    with pytest.raises(ValueError):
        nasa.normalizar("nada aqui\n")


def test_centroide_de_quadrado():
    quadrado = {"type": "Polygon", "coordinates": [[[0, 0], [0, 2], [2, 2], [2, 0], [0, 0]]]}
    lat, lon = ibge.centroide(quadrado)
    assert (round(lat, 6), round(lon, 6)) == (1.0, 1.0)


def test_centroide_de_multipoligono_usa_o_maior():
    pequeno = [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]
    grande = [[[10, 10], [10, 14], [14, 14], [14, 10], [10, 10]]]
    geometria = {"type": "MultiPolygon", "coordinates": [pequeno, grande]}
    lat, lon = ibge.centroide(geometria)
    assert (round(lat, 4), round(lon, 4)) == (12.0, 12.0)


def test_escrever_centroides_do_fixture(bronze):
    caminho = bronze / "malhas" / "uf=41" / "centroides.csv"
    linhas = caminho.read_text().strip().splitlines()
    assert linhas[0] == "codigo_municipio,latitude,longitude"
    assert len(linhas) == 4
    assert all(linha.split(",")[0].startswith("41") for linha in linhas[1:])


def test_ler_clima_converte_doy_em_data():
    from pathlib import Path

    caminho = Path(__file__).parent / "fixtures" / "clima_4127502.csv"
    registros = nasa.ler_clima(caminho)
    assert len(registros) == 242
    assert registros[0]["data"].year == 2021
    assert registros[-1]["data"].year == 2022
    assert all(isinstance(r["PRECTOTCORR"], float | None) for r in registros[:5])
