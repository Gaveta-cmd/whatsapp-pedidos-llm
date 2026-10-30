"""Schema do pedido: a "régua" que define o que é uma ficha de pedido válida.

Todo o projeto usa estas classes: o gerador de dados cria exemplos neste formato,
o modelo é treinado para produzir este formato e a API valida a saída com ele.
"""
import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError

CARDAPIO_PATH = Path(__file__).resolve().parent.parent / "data" / "cardapio.json"

Pagamento = Literal["pix", "dinheiro", "cartão de crédito", "cartão de débito"]


class Item(BaseModel):
    produto: str = Field(min_length=1)
    qtd: int = Field(ge=1, le=99)
    obs: Optional[str] = None


class Pedido(BaseModel):
    itens: list[Item]  # lista vazia = a mensagem não é um pedido (pergunta, saudação, reclamação)
    endereco: Optional[str] = None
    pagamento: Optional[Pagamento] = None


def nomes_do_cardapio() -> set[str]:
    """Nomes canônicos dos produtos que existem no cardápio."""
    dados = json.loads(CARDAPIO_PATH.read_text(encoding="utf-8"))
    return {p["produto"] for g in ("espetinhos", "acompanhamentos", "bebidas") for p in dados[g]}


def produtos_fora_do_cardapio(pedido: Pedido) -> list[str]:
    validos = nomes_do_cardapio()
    return [i.produto for i in pedido.itens if i.produto not in validos]


def parse_saida_do_modelo(texto: str) -> Optional[Pedido]:
    """Tenta transformar o texto que o modelo gerou em um Pedido.

    Devolve None se o texto não for JSON válido ou não obedecer o schema.
    É isso que mede a métrica "% de JSON válido" da tabela do README.
    """
    try:
        return Pedido.model_validate_json(texto)
    except ValidationError:
        return None
