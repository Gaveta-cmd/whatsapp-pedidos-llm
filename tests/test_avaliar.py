import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from avaliar import calcular_metricas, extrair_json

GOLD = {"itens": [{"produto": "espetinho de carne", "qtd": 2, "obs": None},
                  {"produto": "coca-cola lata", "qtd": 1, "obs": "bem gelada"}],
        "endereco": None, "pagamento": "pix"}


def test_resposta_perfeita():
    m = calcular_metricas([json.dumps(GOLD)], [GOLD])
    assert m["json_valido"] == 1 and m["acerto_exato"] == 1 and m["f1_produto_qtd_obs"] == 1


def test_ordem_dos_itens_nao_importa():
    inv = {**GOLD, "itens": GOLD["itens"][::-1]}
    assert calcular_metricas([json.dumps(inv)], [GOLD])["acerto_exato"] == 1


def test_json_invalido_conta_como_erro():
    m = calcular_metricas(["desculpe, não entendi"], [GOLD])
    assert m["json_valido"] == 0 and m["acerto_exato"] == 0


def test_erro_so_na_quantidade_derruba_acerto_exato_mas_nao_o_f1_inteiro():
    errado = {**GOLD, "itens": [{"produto": "espetinho de carne", "qtd": 3, "obs": None}, GOLD["itens"][1]]}
    m = calcular_metricas([json.dumps(errado)], [GOLD])
    assert m["acerto_exato"] == 0 and m["json_valido"] == 1
    assert m["f1_produto_qtd"] == 0.5


def test_extrai_json_de_markdown_e_texto_em_volta():
    txt = 'Claro! ```json\n{"a": 1}\n``` pronto'
    assert extrair_json(txt) == '{"a": 1}'
