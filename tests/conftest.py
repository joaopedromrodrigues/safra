import shutil
from pathlib import Path

import pytest

from safra import config
from safra.ingest import ibge
from safra.transform import warehouse

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def bronze(tmp_path: Path) -> Path:
    """Monta um bronze minimo -- payloads reais da API, recortados -- em particao."""
    base = tmp_path / "bronze"
    pam = base / "ibge_pam" / "ano=2022" / "uf=41"
    pam.mkdir(parents=True)
    shutil.copy(FIXTURES / "sidra_soja_2022.json", pam / "soja.json")
    shutil.copy(FIXTURES / "sidra_estado_2022.json", pam / "estado.json")

    malhas = base / "malhas" / "uf=41"
    malhas.mkdir(parents=True)
    shutil.copy(FIXTURES / "malhas_pr_3.geojson", malhas / "municipios.geojson")
    ibge.escrever_centroides(malhas / "municipios.geojson", malhas / "centroides.csv")

    for arquivo in FIXTURES.glob("clima_*.csv"):
        codigo = arquivo.stem.split("_")[1]
        destino = base / "nasa_power" / f"municipio={codigo}"
        destino.mkdir(parents=True)
        shutil.copy(arquivo, destino / "clima.csv")
    return base


@pytest.fixture
def con(bronze: Path, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "BRONZE", bronze)
    monkeypatch.setattr(config, "DIST", tmp_path / "dist")
    conexao = warehouse.conectar(tmp_path / "safra.duckdb")
    yield conexao
    conexao.close()
