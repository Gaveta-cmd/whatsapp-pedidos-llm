import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from schema import Pedido, parse_saida_do_modelo, produtos_fora_do_cardapio

EXEMPLO_DO_PDF = {
    "itens": [
        {"produto": "espetinho de carne", "qtd": 2, "obs": None},
        {"produto": "espetinho de frango", "qtd": 1, "obs": "sem farofa"},
        {"produto": "coca-cola lata", "qtd": 1, "obs": None},
    ]
}


def test_exemplo_do_pdf_e_valido():
    pedido = parse_saida_do_modelo(json.dumps(EXEMPLO_DO_PDF))
    assert pedido is not None
    assert len(pedido.itens) == 3
    assert produtos_fora_do_cardapio(pedido) == []


def test_json_quebrado_vira_none():
    assert parse_saida_do_modelo('{"itens": [') is None


def test_quantidade_zero_e_invalida():
    ruim = {"itens": [{"produto": "espetinho de carne", "qtd": 0}]}
    assert parse_saida_do_modelo(json.dumps(ruim)) is None


def test_pedido_sem_itens_significa_que_nao_e_pedido():
    p = parse_saida_do_modelo('{"itens": []}')
    assert p is not None and p.itens == []


def test_pagamento_fora_da_lista_e_invalido():
    ruim = {**EXEMPLO_DO_PDF, "pagamento": "fiado"}
    assert parse_saida_do_modelo(json.dumps(ruim)) is None


def test_produto_inventado_e_detectado():
    p = Pedido.model_validate({"itens": [{"produto": "pizza", "qtd": 1}]})
    assert produtos_fora_do_cardapio(p) == ["pizza"]
