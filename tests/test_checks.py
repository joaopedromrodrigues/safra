"""As checagens tem que reprovar o que deveriam reprovar.

Um check que nunca falha nao e check. Aqui o recorte de tres municipios derruba de
proposito a cobertura de area. `recorte_sem_vies` passa porque os tres municipios
sao grandes e parecidos -- o vies so aparece quando o recorte mistura tamanho.
"""

from safra.quality import checks
from safra.transform import warehouse


def test_checks_reprovam_so_a_cobertura(con):
    warehouse.rodar(con)
    resultados = {r.nome: r for r in checks.rodar(con)}

    falhas = {nome for nome, r in resultados.items() if not r.passou}
    assert falhas == {"cobertura_area"}
    assert resultados["grao_unico"].passou
    assert resultados["janela_clima_completa"].passou
    assert resultados["rendimento_na_faixa"].passou
    assert resultados["recorte_sem_vies"].passou


def test_resumo_serializa(con, tmp_path):
    warehouse.rodar(con)
    destino = checks.salvar(checks.rodar(con), tmp_path / "quality.json")
    texto = destino.read_text(encoding="utf-8")
    assert '"ok": false' in texto
    assert "cobertura_area" in texto
