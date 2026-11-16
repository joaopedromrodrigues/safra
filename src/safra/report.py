"""Saida final: tabela no terminal, CSVs em dist/ e a figura de docs/.

A pergunta do projeto -- "o que da chuva explica o rendimento da soja no Parana?" --
e respondida aqui e nao num notebook, para o numero sair igual com `make demo` em
qualquer maquina. O modelo e de proposito pequeno: desvios em relacao a media do
proprio municipio, duas variaveis (chuva e veranico de dez-jan), sem efeito fixo de
safra. Se o leitor quiser prever preco, este nao e o lugar.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import config  # noqa: E402


def series(con: duckdb.DuckDBPyConnection) -> tuple[pd.DataFrame, pd.DataFrame]:
    estado = con.execute("""
        select r.ano_colheita,
               (r.ano_colheita - 1) || '/' || right(r.ano_colheita::varchar, 2) as safra,
               r.rendimento_estado_ibge,
               r.rendimento_municipios,
               r.cobertura_area,
               a.chuva_anomalia_pct_ponderada,
               a.veranico_critica_ponderado_dias,
               a.pct_municipios_secos,
               a.municipios
        from gold.reconciliacao_safra r
        join gold.agg_safra_estado a using (ano_colheita)
        order by r.ano_colheita
    """).fetch_df()
    municipios = con.execute("select * from gold.fct_safra_municipio").fetch_df()
    return estado, municipios


def modelo(municipios: pd.DataFrame) -> dict:
    """Regressao nos desvios, dentro do municipio.

    Duas variaveis de clima e nada mais: com ~9 safras por municipio, cada parametro
    extra come um grau de liberdade e o R2 sobe sem significar nada.
    """
    dados = municipios.dropna(
        subset=["chuva_anomalia_pct", "rendimento_anomalia_pct", "veranico_critica_dias"]
    ).copy()
    dados["veranico_anomalia"] = dados.groupby("codigo_municipio")[
        "veranico_critica_dias"
    ].transform(lambda s: s - s.mean())

    y = pd.Series(dados["rendimento_anomalia_pct"].to_numpy(), index=dados.index)
    x = np.column_stack([
        np.ones(len(dados)),
        dados["chuva_anomalia_pct"].to_numpy(),
        dados["veranico_anomalia"].to_numpy(),
    ])
    beta, *_ = np.linalg.lstsq(x, y.to_numpy(), rcond=None)
    residuo = y.to_numpy() - x @ beta
    r2 = 1 - (residuo**2).sum() / ((y - y.mean()) ** 2).sum()

    return {
        "n_observacoes": int(len(dados)),
        "n_municipios": int(dados["codigo_municipio"].nunique()),
        "r_chuva": round(float(dados["chuva_anomalia_pct"].corr(y)), 3),
        "r_veranico": round(float(dados["veranico_anomalia"].corr(y)), 3),
        "r2": round(float(r2), 3),
        # efeito por unidade: +10 p.p. de chuva na janela critica vs +1 dia de veranico
        "efeito_10pp_chuva": round(float(beta[1] * 0.10) * 100, 2),
        "efeito_dia_veranico": round(float(beta[2]) * 100, 2),
    }


def imprimir(estado: pd.DataFrame, ajuste: dict) -> None:
    print()
    print(f"{'season':<9}{'IBGE':>7}{'cut':>7}{'cover':>7}{'rain anom':>11}"
          f"{'dry spell':>11}{'% dry':>7}")
    for linha in estado.itertuples():
        print(f"{linha.safra:<9}{linha.rendimento_estado_ibge:>7.0f}"
              f"{linha.rendimento_municipios:>7.0f}{linha.cobertura_area:>6.0%}"
              f"{linha.chuva_anomalia_pct_ponderada:>10.1%}"
              f"{linha.veranico_critica_ponderado_dias:>10.1f}d"
              f"{linha.pct_municipios_secos:>7.0%}")
    print()
    print(f"model: deviations inside each municipality, {ajuste['n_observacoes']} obs / "
          f"{ajuste['n_municipios']} municipalities")
    print(f"  corr rain (Dec-Jan)     = {ajuste['r_chuva']:+.2f}"
          f"   (+10 p.p. rain  -> {ajuste['efeito_10pp_chuva']:+.1f}% yield)")
    print(f"  corr dry spell (Dec-Jan)= {ajuste['r_veranico']:+.2f}"
          f"   (+1 dry day     -> {ajuste['efeito_dia_veranico']:+.1f}% yield)")
    print(f"  R2                      = {ajuste['r2']:.2f}")


def figura(estado: pd.DataFrame, municipios: pd.DataFrame, ajuste: dict, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig, (esq, dir_) = plt.subplots(1, 2, figsize=(12, 4.6))

    esq.plot(estado["safra"], estado["rendimento_estado_ibge"], marker="o", color="#1f4e79",
             label="Parana state (IBGE)")
    esq.plot(estado["safra"], estado["rendimento_municipios"], marker="s", linestyle="--",
             color="#c0504d", label="municipality cut")
    esq.set_title("Average soybean yield, Parana")
    esq.set_ylabel("kg/ha")
    esq.set_ylim(2000, 4200)
    esq.tick_params(axis="x", rotation=45)
    esq.legend(frameon=False, fontsize=8)
    esq.grid(alpha=0.25)
    for safra, valor in zip(estado["safra"], estado["rendimento_estado_ibge"], strict=True):
        esq.annotate(f"{valor:,.0f}".replace(",", "."), (safra, valor),
                     textcoords="offset points", xytext=(0, 7), ha="center", fontsize=7)

    dados = municipios.dropna(subset=["veranico_critica_dias", "rendimento_anomalia_pct"])
    pontos = dir_.scatter(dados["veranico_critica_dias"],
                          dados["rendimento_anomalia_pct"] * 100,
                          c=dados["ano_colheita"], cmap="viridis", s=16, alpha=0.7)
    if len(dados) > 2:
        coef = np.polyfit(dados["veranico_critica_dias"], dados["rendimento_anomalia_pct"] * 100, 1)
        grade = np.linspace(dados["veranico_critica_dias"].min(),
                            dados["veranico_critica_dias"].max(), 20)
        dir_.plot(grade, np.polyval(coef, grade), color="#444", linewidth=1.2)
    dir_.axhline(0, color="#999", linewidth=0.8)
    dir_.set_title(f"Dry spell in Dec-Jan vs yield deviation (r={ajuste['r_veranico']:+.2f})")
    dir_.set_xlabel("longest run of days with less than 1 mm of rain")
    dir_.set_ylabel("yield deviation from the municipality mean (%)")
    dir_.grid(alpha=0.25)
    fig.colorbar(pontos, ax=dir_, label="harvest year")

    fig.tight_layout()
    fig.savefig(destino, dpi=150)
    plt.close(fig)
    return destino


def exportar(con: duckdb.DuckDBPyConnection, destino: Path = config.DIST) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    saidas = []
    for tabela in ("agg_safra_estado", "reconciliacao_safra", "fct_safra_municipio",
                   "dim_municipio"):
        caminho = destino / f"{tabela}.csv"
        con.execute(f"copy gold.{tabela} to '{caminho}' (header, delimiter ',')")
        saidas.append(caminho)
    return saidas
