import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from gerar_dados import carregar_cardapio, gerar
from schema import Pedido, produtos_fora_do_cardapio


def test_todo_pedido_gerado_e_valido_e_esta_no_cardapio():
    for ex in gerar(300, seed=1):
        pedido = Pedido.model_validate(ex["pedido"])
        assert produtos_fora_do_cardapio(pedido) == []


def test_endereco_aparece_literalmente_na_mensagem():
    com_end = [e for e in gerar(500, seed=5) if e["pedido"]["endereco"]]
    assert com_end
    for e in com_end:
        assert e["pedido"]["endereco"] in e["mensagem"]


def test_de_cada_espetinho_expande_para_todos_os_cinco():
    frases = ("de cada espetinho", "de cada tipo de espetinho", "de cada espeto")
    exs = [e for e in gerar(2500, seed=9) if any(f in e["mensagem"] for f in frases)]
    assert exs
    for e in exs:
        esp = [i for i in e["pedido"]["itens"] if i["produto"].startswith("espetinho")]
        assert len(esp) == len(carregar_cardapio()["espetinhos"]) and len({i["qtd"] for i in esp}) == 1


def test_de_cada_acompanhamento_expande_para_os_quatro():
    exs = [e for e in gerar(3000, seed=9) if "de cada" in e["mensagem"] and "acompanhamento" in e["mensagem"]]
    assert exs
    nomes = {p["produto"] for p in carregar_cardapio()["acompanhamentos"]}
    for e in exs:
        assert nomes <= {i["produto"] for i in e["pedido"]["itens"]}


def test_mensagens_sem_pedido_tem_itens_vazio():
    exs = gerar(500, seed=21)
    vazios = [e for e in exs if e["pedido"]["itens"] == []]
    assert 15 <= len(vazios) <= 80  # ~8%
    assert all(e["pedido"]["endereco"] is None and e["pedido"]["pagamento"] is None for e in vazios)


def test_item_fora_do_cardapio_nunca_entra_no_gabarito():
    from gerar_dados import FORA_CARDAPIO
    exs = gerar(1500, seed=4)
    com_fora = [e for e in exs if any(f in e["mensagem"] for f in ("batata frita", "red bull", "pizza", "cupim"))]
    assert com_fora
    for e in com_fora:
        for i in e["pedido"]["itens"]:
            assert i["produto"] not in FORA_CARDAPIO


def test_frases_novas_de_pagamento_existem_e_mapeiam_certo():
    exs = gerar(2000, seed=11)
    chave = [e for e in exs if "chave" in e["mensagem"] and e["pedido"]["pagamento"]]
    assert chave and all(e["pedido"]["pagamento"] == "pix" for e in chave)
    troco = [e for e in exs if "troco" in e["mensagem"] and e["pedido"]["pagamento"]]
    assert troco and all(e["pedido"]["pagamento"] == "dinheiro" for e in troco)


def test_caprichar_vira_obs_em_acompanhamento():
    exs = gerar(2000, seed=13)
    com = [i for e in exs for i in e["pedido"]["itens"] if i["obs"] == "caprichar"]
    assert com and all(i["produto"].startswith(("porção", "pão")) for i in com)
    sem_numero = [e for e in exs if "capricha na" in e["mensagem"]]
    assert sem_numero
    for e in sem_numero:
        assert any(i["obs"] == "caprichar" and i["qtd"] == 1 for i in e["pedido"]["itens"])


def test_v4_tem_maiusculas_e_ponto_final_em_boa_parte_das_mensagens():
    msgs = [e["mensagem"] for e in gerar(1000, seed=31)]
    com_maiuscula = sum(m[:1].isupper() for m in msgs)
    com_ponto_final = sum(m.rstrip()[-1:] in ".!?" for m in msgs)
    assert 250 < com_maiuscula < 750      # ~metade em caixa de frase
    assert com_ponto_final > 250          # pontuação no fim aparece bastante


def test_reclamacao_com_rua_nao_vira_endereco():
    exs = gerar(3000, seed=17)
    rec = [e for e in exs if e["pedido"]["itens"] == [] and any(
        k in e["mensagem"].lower() for k in ("saiu pra entrega", "cadê meu pedido", "tá demorando"))]
    assert rec and all(e["pedido"]["endereco"] is None for e in rec)


def test_troco_abreviado_continua_sendo_dinheiro():
    exs = gerar(3000, seed=19)
    t = [e for e in exs if ("troco p 100" in e["mensagem"].lower() or "troco p/ 50" in e["mensagem"].lower())
         and e["pedido"]["pagamento"]]
    assert t and all(e["pedido"]["pagamento"] == "dinheiro" for e in t)


def test_mensagens_proibidas_nao_aparecem():
    base = gerar(200, seed=2)
    proib = frozenset(e["mensagem"] for e in base)
    novas = gerar(200, seed=2, proibidas=proib)
    assert not proib & {e["mensagem"] for e in novas}


def test_mesma_seed_gera_os_mesmos_dados():
    assert gerar(50, seed=7) == gerar(50, seed=7)


def test_sem_mensagens_repetidas():
    msgs = [e["mensagem"] for e in gerar(500, seed=3)]
    assert len(msgs) == len(set(msgs))
