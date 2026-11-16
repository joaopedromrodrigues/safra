"""CLI: `python -m safra run` faz o ciclo inteiro.

As opcoes valem tanto antes quanto depois do subcomando (`safra --anos 2020 run`
e `safra run --anos 2020`). Para isso o parser comum usa SUPPRESS: quem nao foi
passado num nivel nao sobrescreve o valor do outro.
"""

from __future__ import annotations

import argparse
import sys

from . import config, pipeline

COMANDOS = ("ingest", "build", "check", "report", "run")
AJUDA = {
    "ingest": "baixa bronze",
    "build": "monta silver e gold",
    "check": "roda as checagens de qualidade",
    "report": "exporta dist/ e a figura",
    "run": "ciclo completo (default)",
}


def construir_parser() -> argparse.ArgumentParser:
    comum = argparse.ArgumentParser(add_help=False)
    comum.add_argument("--anos", default=argparse.SUPPRESS,
                       help=f"anos de colheita, ex.: {config.PRIMEIRO_ANO}-{config.ULTIMO_ANO}")
    comum.add_argument("--municipios", default=argparse.SUPPRESS,
                       help="numero fixo de municipios a puxar do POWER, ou 'all'")
    comum.add_argument("--cobertura", type=float, default=argparse.SUPPRESS,
                       help="fracao da area plantada do estado que o recorte deve cobrir "
                            "(ignorado quando --municipios e passado)")
    comum.add_argument("--force", action="store_true", default=argparse.SUPPRESS,
                       help="ignora o cache e baixa de novo")

    parser = argparse.ArgumentParser(prog="safra", description="soja x clima no Parana",
                                     parents=[comum])
    sub = parser.add_subparsers(dest="comando")
    for comando in COMANDOS:
        sub.add_parser(comando, help=AJUDA[comando], parents=[comum])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    anos = config.anos(getattr(args, "anos", None))
    municipios = getattr(args, "municipios", None)
    cobertura = getattr(args, "cobertura", 0.85)
    force = getattr(args, "force", False)
    comando = args.comando or "run"

    if comando == "build":
        pipeline.montar_warehouse()
        return 0
    if comando == "check":
        return 0 if pipeline.validar() else 1
    if comando == "report":
        pipeline.publicar()
        return 0

    pipeline.ingerir_pam(anos, force)
    pipeline.ingerir_malhas(force)
    pipeline.montar_silver_parcial()
    pipeline.ingerir_clima(municipios, cobertura, force)
    if comando == "ingest":
        return 0

    pipeline.montar_warehouse()
    ok = pipeline.validar()
    pipeline.publicar()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
