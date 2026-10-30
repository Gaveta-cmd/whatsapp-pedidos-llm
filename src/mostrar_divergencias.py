"""Mostra, em formato curto, onde o modelo treinado e o Claude divergiram nas mensagens reais."""
import json
from pathlib import Path

from avaliar import carregar_jsonl, pedidos_iguais
from schema import Pedido, parse_saida_do_modelo

RAIZ = Path(__file__).resolve().parent.parent


def resumo(p: Pedido | None) -> str:
    if p is None:
        return "JSON INVALIDO"
    itens = "; ".join(f"{i.qtd}x {i.produto}" + (f" [{i.obs}]" if i.obs else "") for i in p.itens)
    return f"{itens} | end={p.endereco} | pag={p.pagamento}"


def main() -> None:
    linhas = carregar_jsonl(RAIZ / "outputs" / "resultados" / "reais_comparacao.jsonl")
    iguais = 0
    for n, l in enumerate(linhas, 1):
        c, m = parse_saida_do_modelo(l["claude"]), parse_saida_do_modelo(l["lora"])
        if c is not None and m is not None and pedidos_iguais(c, m):
            iguais += 1
            continue
        print(f"#{n} {l['mensagem']}")
        print(f"   CLAUDE: {resumo(c)}")
        print(f"   LORA  : {resumo(m)}\n")
    print(f"concordam: {iguais}/{len(linhas)}")


if __name__ == "__main__":
    main()
