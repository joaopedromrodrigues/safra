"""Argumentos da CLI: as duas ordens de opcao tem que funcionar.

O `make demo` passava `run --anos ...`, que o argparse recusava porque as opcoes
estavam so no parser de cima. Este teste existe para isso nao voltar.
"""

from safra import cli


def test_opcao_antes_do_comando():
    args = cli.construir_parser().parse_args(["--anos", "2020-2022", "run"])
    assert args.comando == "run"
    assert args.anos == "2020-2022"


def test_opcao_depois_do_comando():
    args = cli.construir_parser().parse_args(["run", "--anos", "2020-2022", "--cobertura", "0.5"])
    assert args.anos == "2020-2022"
    assert args.cobertura == 0.5


def test_sem_comando_assume_run():
    args = cli.construir_parser().parse_args([])
    assert args.comando is None
    assert not hasattr(args, "anos"), "sem opcao passada, o default vem do config e nao do parser"
