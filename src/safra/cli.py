"""CLI: `python -m safra run` faz o ciclo inteiro."""

from __future__ import annotations

import argparse
import sys

from . import config, pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="safra", description="soja x clima no Parana")
    parser.add_argument("--anos", default=f"{config.PRIMEIRO_ANO}-{config.ULTIMO_ANO}",
                        help="intervalo de anos de colheita, ex.: 2018-2024")
    parser.add_argument("--municipios", default=None,
                        help="numero fixo de municipios a puxar do POWER, ou 'all'")
    parser.add_argument("--cobertura", type=float, default=0.85,
                        help="fracao da area plantada do estado que o recorte deve cobrir "
                             "(ignorado quando --municipios e passado)")
    parser.add_argument("--force", action="store_true", help="ignora o cache e baixa de novo")
    sub = parser.add_subparsers(dest="comando")

    sub.add_parser("ingest", help="baixa bronze")
    sub.add_parser("build", help="monta silver e gold")
    sub.add_parser("check", help="roda as checagens de qualidade")
    sub.add_parser("report", help="exporta dist/ e a figura")
    sub.add_parser("run", help="ciclo completo (default)")

    args = parser.parse_args(argv)
    anos = config.anos(args.anos)
    comando = args.comando or "run"

    if comando == "ingest":
        pipeline.ingerir_pam(anos, args.force)
        pipeline.ingerir_malhas(args.force)
        pipeline.montar_silver_parcial()
        pipeline.ingerir_clima(args.municipios, args.cobertura, args.force)
        return 0
    if comando == "build":
        pipeline.montar_warehouse()
        return 0
    if comando == "check":
        return 0 if pipeline.validar() else 1
    if comando == "report":
        pipeline.publicar()
        return 0

    pipeline.ingerir_pam(anos, args.force)
    pipeline.ingerir_malhas(args.force)
    pipeline.montar_silver_parcial()
    pipeline.ingerir_clima(args.municipios, args.cobertura, args.force)
    pipeline.montar_warehouse()
    ok = pipeline.validar()
    pipeline.publicar()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
