"""Diagnóstico: o defeito "perde o último item" é da Coca 2L ou da posição/pontuação?

Experimento controlado: a MESMA frase-molde, trocando só o último item (X), em vários modelos de frase
(com fim de frase depois da lista, sem nada depois, sem pontuação). Para cada X conta quantas vezes o
modelo manteve o último item e quantas manteve todos os itens esperados.
Não treina nada e não usa a API do Claude (sem custo). As frases-molde são novas, escritas para este teste.

Uso: python src/diagnosticar_item_final.py --adapter outputs/lora-qwen1.5b-v5 --nome v5
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from avaliar_final import SAIDA, parse, rodar_lora

# (frase com {X}, itens que NÃO são o último, em (produto, qtd))
MOLDES = {
    "fim de frase + pagamento": (
        "Boa noite! Quero 3 espetinhos de frango, 2 porções de mandioca e {X}. Pagamento no cartão de débito, por favor.",
        [("espetinho de frango", 3), ("porção de mandioca frita", 2)]),
    "fim de frase curto": (
        "Olá, gostaria de 2 espetinhos de carne, 1 pão de alho e {X}. Vou pagar no Pix.",
        [("espetinho de carne", 2), ("pão de alho", 1)]),
    "agradecimento": (
        "Boa tarde. Me manda 4 espetinhos de linguiça, 2 espetinhos de coração e {X}. Obrigado!",
        [("espetinho de linguiça", 4), ("espetinho de coração", 2)]),
    "nada depois": (
        "Por favor, 5 espetinhos de queijo coalho, 1 porção de vinagrete e {X}.",
        [("espetinho de queijo coalho", 5), ("porção de vinagrete", 1)]),
    "sem pontuação": (
        "boa noite quero 3 espetinhos de frango 2 porcoes de mandioca e {X} pago no pix",
        [("espetinho de frango", 3), ("porção de mandioca frita", 2)]),
    "endereço depois": (
        "Quero 2 espetinhos de carne, 2 de frango e {X}. Entregar na Rua das Flores, 55. Dinheiro, com troco para 50.",
        [("espetinho de carne", 2), ("espetinho de frango", 2)]),
}

# texto do último item -> (produto esperado, qtd)
FINAIS = {
    "1 Coca 2L": ("coca-cola 2l", 1),
    "1 Coca-Cola 2L": ("coca-cola 2l", 1),
    "1 Coca de 2 litros": ("coca-cola 2l", 1),
    "1 Coca-Cola lata": ("coca-cola lata", 1),
    "1 Guaraná lata": ("guaraná lata", 1),
    "1 suco de laranja": ("suco de laranja", 1),
    "1 água sem gás": ("água sem gás", 1),
    "1 pão de alho": ("pão de alho", 1),
    "1 farofa": ("porção de farofa", 1),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--nome", required=True)
    a = ap.parse_args()

    casos = [(molde, x, frase.format(X=x), outros, FINAIS[x])
             for molde, (frase, outros) in MOLDES.items() for x in FINAIS]
    saidas = rodar_lora([c[2] for c in casos], a.adapter)

    por_final = {x: Counter() for x in FINAIS}
    por_molde = {m: Counter() for m in MOLDES}
    erros = []
    for (molde, x, frase, outros, (prod, qtd)), bruto in zip(casos, saidas):
        pred = parse(bruto)
        itens = Counter((i.produto.lower(), i.qtd) for i in pred.itens) if pred else Counter()
        ultimo = itens[(prod, qtd)] >= 1
        todos = ultimo and all(itens[o] >= 1 for o in outros)
        for c in (por_final[x], por_molde[molde]):
            c["n"] += 1
            c["ultimo_presente"] += ultimo
            c["todos_presentes"] += todos
        if not ultimo:
            erros.append({"molde": molde, "final": x, "mensagem": frase, "saida": bruto})

    resumo = {"por_ultimo_item": {k: dict(v) for k, v in por_final.items()},
              "por_molde": {k: dict(v) for k, v in por_molde.items()},
              "total": {"n": len(casos), "ultimo_presente": sum(v["ultimo_presente"] for v in por_final.values()),
                        "todos_presentes": sum(v["todos_presentes"] for v in por_final.values())},
              "erros_do_ultimo_item": erros}
    (SAIDA / f"diagnostico_item_final_{a.nome}.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(a.nome, "total:", resumo["total"])
    print("por último item (mantido/total):")
    for x, v in por_final.items():
        print(f"  {x:22} {v['ultimo_presente']}/{v['n']}")
    print("por molde (mantido/total):")
    for m, v in por_molde.items():
        print(f"  {m:26} {v['ultimo_presente']}/{v['n']}")


if __name__ == "__main__":
    main()
