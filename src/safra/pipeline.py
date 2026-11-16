"""Etapas do pipeline, uma funcao por task.

A CLI e a DAG do Airflow chamam estas funcoes. Deixar a logica aqui (e nao no
`cli.py`) evita que o orquestrador precise saber argparse, e deixa cada etapa
testavel sem subir scheduler.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from . import config, report
from .ingest import ibge, nasa
from .quality import checks
from .transform import warehouse


def _log(msg: str) -> None:
    print(f"[safra] {msg}", flush=True)


def anos_do_projeto(intervalo: str | None = None) -> list[int]:
    return config.anos(intervalo)


def ingerir_pam(anos: list[int] | None = None, force: bool = False) -> dict:
    anos = anos or config.anos()
    coletas = ibge.baixar_pam(anos, force=force)
    novos = sum(1 for c in coletas if c["status"] == "baixado")
    _log(f"PAM: {novos} arquivos novos, {len(coletas) - novos} em cache")
    return {"anos": anos, "novos": novos, "total": len(coletas)}


def ingerir_malhas(force: bool = False) -> dict:
    coleta = ibge.baixar_malhas(force=force)
    _log(f"malhas: {coleta['status']}")
    return coleta


def montar_silver_parcial() -> None:
    """PAM e centroides: precisa existir antes de escolher quais municipios pedir."""
    con = warehouse.conectar()
    try:
        for nome, segundos in warehouse.rodar(con, "0[1-3]*.sql"):
            _log(f"sql {nome} ({segundos}s)")
    finally:
        con.close()


def ingerir_clima(municipios: str | None = None, cobertura: float = 0.85,
                  force: bool = False) -> dict:
    con = warehouse.conectar()
    try:
        if municipios in (None, "cobertura"):
            alvo = warehouse.municipios_por_area(con, cobertura=cobertura)
        elif municipios == "all":
            alvo = warehouse.municipios_por_area(con)
        else:
            alvo = warehouse.municipios_por_area(con, quantos=int(municipios))
    except duckdb.CatalogException as exc:
        raise SystemExit("monte o silver (PAM + malhas) antes de pedir o clima") from exc
    finally:
        con.close()

    alvo = [m for m in alvo if m["latitude"] is not None]
    area = sum(m["area_plantada_ha"] for m in alvo)
    _log(f"clima: {len(alvo)} municipios, {area:,.0f} ha no recorte".replace(",", "."))
    _log(f"clima: pedido {config.periodo_power()[0]}..{config.periodo_power()[1]}")
    coletas = nasa.baixar_clima(alvo, force=force)
    novos = sum(1 for c in coletas if c["status"] == "baixado")
    _log(f"clima: {novos} arquivos novos, {len(coletas) - novos} em cache")
    return {"municipios": len(alvo), "novos": novos}


def montar_warehouse() -> None:
    con = warehouse.conectar()
    try:
        for nome, segundos in warehouse.rodar(con):
            _log(f"sql {nome} ({segundos}s)")
    finally:
        con.close()


def validar() -> bool:
    con = warehouse.conectar()
    try:
        resultados = checks.rodar(con)
    finally:
        con.close()
    for r in resultados:
        _log(f"check {'ok  ' if r.passou else 'FALHA'} {r.nome}: {r.medido} "
             f"(esperado {r.limite})")
    _log(f"checks em {checks.salvar(resultados)}")
    return all(r.passou for r in resultados)


def publicar(destino: Path | None = None) -> dict:
    con = warehouse.conectar()
    try:
        estado, municipios = report.series(con)
        ajuste = report.modelo(municipios)
        caminhos = report.exportar(con, destino or config.DIST)
    finally:
        con.close()
    _log(f"export: {', '.join(p.name for p in caminhos)}")
    figura = report.figura(estado, municipios, ajuste,
                           Path("docs") / "figuras" / "rendimento_veranico.png")
    report.imprimir(estado, ajuste)
    _log(f"figura: {figura}")
    return {"exportados": [str(p) for p in caminhos], "figura": str(figura), "modelo": ajuste}
