"""Pipeline inteiro sem rede: bronze de fixture -> silver -> gold -> checks.

Os fixtures sao respostas reais do SIDRA, das malhas e do POWER, recortadas para
tres municipios e uma safra. Se o formato de alguma das APIs mudar, este teste
quebra antes de quebrar em producao.
"""

from safra.transform import warehouse

MUNICIPIO_REFERENCIA = "4127502"  # Tibagi, maior area plantada de soja do PR


def test_todas_as_etapas_rodam(con):
    tempos = warehouse.rodar(con)
    assert len(tempos) == 8, [nome for nome, _ in tempos]
    assert all(segundos < 30 for _, segundos in tempos)


def test_grao_do_fato(con):
    warehouse.rodar(con)
    assert warehouse.contagem(con, "gold.fct_safra_municipio") == 3
    duplicados = con.execute("""
        select count(*) from (
            select codigo_municipio, ano_colheita from gold.fct_safra_municipio
            group by 1, 2 having count(*) > 1
        )
    """).fetchone()[0]
    assert duplicados == 0


def test_rendimento_e_clima_do_municipio_de_referencia(con):
    warehouse.rodar(con)
    rendimento, chuva, veranico = con.execute(f"""
        select rendimento_kg_ha, chuva_critica_mm, veranico_critica_dias
        from gold.fct_safra_municipio where codigo_municipio = '{MUNICIPIO_REFERENCIA}'
    """).fetchone()
    # a PAM publicou 3.771 kg/ha para Tibagi na safra 2021/22
    assert 3000 < rendimento < 5000
    assert 100 < chuva < 1200
    assert 0 < veranico <= 62


def test_janela_de_clima_completa(con):
    warehouse.rodar(con)
    cobertura = con.execute(
        "select min(cobertura_janela) from gold.fct_safra_municipio"
    ).fetchone()[0]
    assert cobertura > 0.99


def test_reconciliacao_usa_o_total_do_estado(con):
    warehouse.rodar(con)
    cobertura, producao = con.execute("""
        select cobertura_area, cobertura_producao from gold.reconciliacao_safra
    """).fetchone()
    # tres municipios de duzentos e poucos: tem que ser pequeno, mas nao zero
    assert 0.01 < cobertura < 0.10
    assert producao > cobertura  # soja de alto rendimento concentra producao
