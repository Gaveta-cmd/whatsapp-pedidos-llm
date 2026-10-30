"""Instrução (prompt) enviada aos modelos. Igual para o modelo base e para o Claude: comparação justa."""
import json

from schema import nomes_do_cardapio

PAGAMENTOS = ["pix", "dinheiro", "cartão de crédito", "cartão de débito"]


# Prompt CURTO usado no treino e na avaliação do modelo ajustado. Ele não precisa de cardápio nem de
# regras na instrução: aprendeu isso nos pesos. Menos tokens de entrada = mais rápido e mais barato.
SYSTEM_CURTO = "Extraia o pedido da mensagem em JSON."


def mensagens_curtas(mensagem: str) -> list[dict]:
    return [{"role": "system", "content": SYSTEM_CURTO}, {"role": "user", "content": mensagem}]


def pedido_para_texto(pedido: dict) -> str:
    """Formato compacto que o modelo deve escrever (menos tokens para gerar)."""
    return json.dumps(pedido, ensure_ascii=False, separators=(",", ":"))


REGRAS_DE_NEGOCIO = """
Regras adicionais do restaurante:
- Se o cliente pede a chave ou o QR code do pix, o pagamento é "pix".
- "troco pra 50", "sem troco" ou "dinheiro certinho" indicam pagamento "dinheiro".
- "N de cada espetinho" significa N de CADA um dos espetinhos do cardápio; "N de cada acompanhamento" significa N de CADA um dos acompanhamentos do cardápio.
- Pedir para "caprichar" em um item vira obs "caprichar" nesse item (qtd 1 se o cliente não disse número).
- Perguntas soltas (taxa, horário, prazo de entrega) não viram dado no JSON.
- Produtos que NÃO estão no cardápio são ignorados.
- Se a mensagem não for um pedido (pergunta, saudação, reclamação), responda com "itens": []."""


def system_prompt(com_regras: bool = False) -> str:
    produtos = "\n".join(f"- {p}" for p in sorted(nomes_do_cardapio()))
    base = f"""Você extrai pedidos de um espetinho a partir de mensagens de WhatsApp em português.
Responda SOMENTE com um JSON, sem explicações e sem markdown, neste formato:
{{"itens": [{{"produto": str, "qtd": int, "obs": str ou null}}], "endereco": str ou null, "pagamento": str ou null}}

Regras:
- "produto" deve ser EXATAMENTE um destes nomes do cardápio:
{produtos}
- "qtd" é um número inteiro (converta "dois", "duas" etc.).
- "obs" guarda observações do item (ex.: "sem farofa", "bem passado"); use null se não houver.
- "pagamento" deve ser um de: {", ".join(PAGAMENTOS)}; use null se o cliente não disse.
- "endereco" é o endereço de entrega; use null se o cliente não disse.
- Corrija erros de digitação e gírias para o nome oficial do produto."""
    return base + (REGRAS_DE_NEGOCIO if com_regras else "")
