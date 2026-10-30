"""Gerador de dados sintéticos: cria pares (mensagem do cliente -> pedido correto).

Como funciona: sorteamos primeiro o PEDIDO CORRETO (a resposta), depois escrevemos a
MENSAGEM que um cliente escreveria para pedir aquilo (gíria, erro de digitação, etc.).
Assim a resposta certa é sempre conhecida, sem precisar rotular nada à mão.

v3 acrescenta o que a prova final mostrou que faltava: mensagens SEM pedido (itens vazio), menção a
produtos que NÃO existem no cardápio (devem ser ignorados), "de cada acompanhamento", quantidade depois
do produto ("linguiça 2"), frases condicionais e endereços em formatos variados.

Uso: python src/gerar_dados.py --n 2500 --seed 42 --manter-teste
Saída: data/train.jsonl, data/val.jsonl, data/test.jsonl
"""
import argparse
import json
import random
from pathlib import Path

from schema import CARDAPIO_PATH, Pedido

DATA_DIR = CARDAPIO_PATH.parent

SAUDACOES = ["", "", "oi", "oi, tudo bem?", "boa noite", "boa tarde", "bom dia", "opa", "e aí",
             "ola boa noite", "fala parceiro", "boa noite, tudo bem?", "salve", "fala chefe", "eai blz?",
             "boa noite chefe", "opa boa noite mestre", "fala irmão", "boa tarde rapaziada"]
# Frases soltas que clientes reais mandam junto do pedido e que NÃO viram dado no JSON.
RUIDOS = ["vcs entregam aqui?", "quanto tempo pra entregar?", "quanto fica a taxa de entrega?",
          "vcs tão entregando hj?", "quanto fica tudo?", "tá aberto?", "blz?"]
ABERTURAS = ["quero", "queria", "me vê", "me manda", "vou querer", "pode ser", "preciso de",
             "gostaria de", "quero pedir", "manda", "separa pra mim"]
LIGACOES = [", ", " e ", ", ", " + ", " e mais ", ", mais ", " ", " "]
FECHAMENTOS = ["", "", "", "obrigado", "valeu", "pfv", "por favor", "obg", "é isso"]

NUM_PALAVRA = {1: ["um", "uma", "1"], 2: ["dois", "duas", "2"], 3: ["três", "tres", "3"],
               4: ["quatro", "4"], 5: ["cinco", "5"], 6: ["seis", "6"]}
FEMININO = {"porção", "água", "coca", "lata"}

OBS_ESPETINHO = ["sem farofa", "sem vinagrete", "bem passado", "ao ponto", "mal passado",
                 "sem pimenta", "com pimenta", "sem cebola"]
OBS_BEBIDA = ["sem gelo", "bem gelada"]

PAGAMENTOS = {
    "pix": ["pago no pix", "vai ser pix", "pix", "pagamento no pix", "manda a chave pix",
            "qual a chave do pix?", "me passa o pix", "manda o qr code do pix", "chave pix por favor",
            "paga no pix, manda a chave"],
    "dinheiro": ["pago em dinheiro", "dinheiro", "pago na entrega em dinheiro", "vai ser dinheiro",
                 "dinheiro, troco pra 50", "dinheiro troco pra 100", "em dinheiro, sem troco",
                 "dinheiro certinho", "preciso de troco pra 50, dinheiro"],
    "cartão de crédito": ["no crédito", "cartão de crédito", "credito", "passa no crédito",
                          "crédito na entrega", "maquininha no crédito", "cartão de crédito na entrega",
                          "credito na maquininha"],
    "cartão de débito": ["no débito", "cartão de débito", "debito", "passa no débito",
                         "débito na maquininha", "debito na entrega", "maquininha no débito",
                         "cartão de débito na entrega"],
}
RUAS = ["rua das flores", "av brasil", "rua sete de setembro", "rua dos pinheiros", "av paulista",
        "rua goiás", "rua 15 de novembro", "av getúlio vargas", "rua das acácias", "travessa são jorge",
        "av sul", "rua das mangueiras", "av das nações", "rua do comércio", "rua santo antônio"]
MARCADOR_END = "endereco0"
ABREV = {"por favor": "pfv", "você": "vc", "para": "pra", "que": "q", "obrigado": "obg", "também": "tb"}

# Coisas que o cliente pede/pergunta e que NÃO existem no cardápio: o modelo deve ignorá-las.
FORA_CARDAPIO = ["batata frita", "cerveja heineken", "cerveja skol lata", "pastel", "cupim",
                 "maionese caseira", "red bull", "pizza", "hambúrguer", "sorvete", "fanta",
                 "pão de queijo", "salada", "costela", "coca zero", "suco de uva", "vinho", "carne de sol",
                 "queijo provolone", "farinha", "espeto de cupim", "feijão tropeiro",
                 "molho de alho", "caldo de cana", "cerveja"]
# Mensagens que não são pedido (resposta correta: itens vazio). {p} = um produto do cardápio.
PERGUNTAS = ["até que horas vcs ficam abertos?", "vcs abrem domingo?", "qual o endereço de vcs?",
             "vcs aceitam vale refeição?", "aceitam sodexo ou alelo?", "tem desconto pra retirar aí?",
             "qual o valor da entrega pro centro?", "vcs tão funcionando hj?", "aceitam cartão?",
             "dá pra mandar o cardápio?", "tem estacionamento aí?", "qual o telefone de vcs?",
             "vcs fazem evento? quanto sai?", "quanto custa o {p}?", "tem {p} hoje?",
             "o {p} é grande?", "como faço pra cancelar meu pedido?", "meu pedido ainda não chegou",
             "demora quanto pra entregar?", "obrigado, chegou tudo certo!", "valeu pelo atendimento",
             "vcs entregam em outro bairro?", "tem opção vegetariana?", "posso ir comer aí no balcão?",
             "oi", "bom dia", "boa noite", "alguém aí?", "vocês têm wi-fi?", "ainda tá aberto?"]


def carregar_cardapio() -> dict:
    return json.loads(CARDAPIO_PATH.read_text(encoding="utf-8"))


def digitar_errado(texto: str, rng: random.Random, taxa: float) -> str:
    """Simula erros de digitação: troca, esquece ou repete uma letra (nunca mexe em números)."""
    palavras = texto.split(" ")
    saida = []
    for p in palavras:
        if len(p) > 3 and not any(c.isdigit() for c in p) and rng.random() < taxa:
            i = rng.randrange(1, len(p) - 1)
            tipo = rng.choice(["troca", "esquece", "repete"])
            if tipo == "troca":
                p = p[:i] + p[i + 1] + p[i] + p[i + 2:]
            elif tipo == "esquece":
                p = p[:i] + p[i + 1:]
            else:
                p = p[:i] + p[i] + p[i:]
        saida.append(p)
    return " ".join(saida)


def sortear_endereco(rng: random.Random) -> str:
    """Endereços em formatos variados; o gabarito é sempre a cópia literal do que o cliente escreveu."""
    r = rng.random()
    rua, n = rng.choice(RUAS), rng.randint(1, 999)
    if r < 0.55:
        return f"{rua}, {n}"
    if r < 0.67:
        return f"{rua} num {n}"
    if r < 0.79:
        return f"{rua} {n}"
    if r < 0.86:
        return f"quadra {rng.randint(1, 30)} conjunto {rng.randint(1, 9)} casa {rng.randint(1, 40)}"
    if r < 0.93:
        return f"rua {rng.randint(1, 20)} bloco {rng.choice('ABCD')} apto {rng.randint(101, 504)}"
    return f"{rng.choice(['av sul', 'av norte', 'av das nações'])} lote {rng.randint(1, 40)}"


def sortear_pedido(cardapio: dict, rng: random.Random) -> tuple[Pedido, list[dict], dict]:
    """Sorteia a resposta certa. Devolve também os itens crus (com a categoria) e um contexto de escrita."""
    n_itens = rng.choices([1, 2, 3, 4, 5], weights=[15, 35, 30, 15, 5])[0]
    pool = [(g, p) for g in ("espetinhos", "acompanhamentos", "bebidas") for p in cardapio[g]]
    cada = rng.random() < 0.08  # "N de cada espetinho/acompanhamento": expande para todos do grupo
    grupo_cada = rng.choice(["espetinhos", "espetinhos", "espetinhos", "acompanhamentos"]) if cada else None
    qtd_cada = rng.choice([1, 1, 2])
    if cada:
        do_grupo = [(grupo_cada, p) for p in cardapio[grupo_cada]]
        outros = rng.sample([x for x in pool if x[0] != grupo_cada], rng.choice([0, 1, 2]))
        escolhidos = do_grupo + outros
    else:
        escolhidos = rng.sample(pool, n_itens)
    crus = []
    for grupo, prod in escolhidos:
        if cada and grupo == grupo_cada:
            crus.append({"grupo": grupo, "produto": prod["produto"], "apelidos": prod["apelidos"],
                         "qtd": qtd_cada, "obs": None, "cada": True})
            continue
        qtd = rng.choices([1, 2, 3, 4, 5, 6], weights=[40, 30, 12, 10, 5, 3])[0]
        obs = None
        if grupo == "espetinhos" and rng.random() < 0.3:
            obs = rng.choice(OBS_ESPETINHO)
        elif grupo == "bebidas" and rng.random() < 0.15:
            obs = rng.choice(OBS_BEBIDA)
        elif grupo == "acompanhamentos" and rng.random() < 0.10:
            obs = "caprichar"  # decisão do usuário: "capricha na farofa" = 1 farofa com obs "caprichar"
        crus.append({"grupo": grupo, "produto": prod["produto"], "apelidos": prod["apelidos"],
                     "qtd": qtd, "obs": obs})
    endereco = sortear_endereco(rng) if rng.random() < 0.35 else None
    pagamento = rng.choice(list(PAGAMENTOS)) if rng.random() < 0.35 else None
    pedido = Pedido(
        itens=[{"produto": c["produto"], "qtd": c["qtd"], "obs": c["obs"]} for c in crus],
        endereco=endereco, pagamento=pagamento,
    )
    ctx = {"grupo_cada": grupo_cada, "fora": [], "modo_fora": None}
    if rng.random() < 0.18:  # menciona algo que não existe no cardápio (o gabarito ignora)
        ctx["fora"] = rng.sample(FORA_CARDAPIO, rng.choice([1, 1, 2]))
        ctx["modo_fora"] = rng.choice(["pergunta", "pedido", "condicional"])
    return pedido, crus, ctx


def escrever_item(c: dict, rng: random.Random) -> str:
    apelido = rng.choice(c["apelidos"])
    num = rng.choice(NUM_PALAVRA[c["qtd"]])
    if c["qtd"] == 1 and rng.random() < 0.5:
        num = rng.choice(["um", "uma", "1"])
    if c["qtd"] == 2 and num == "dois" and apelido.split()[0] in FEMININO:
        num = "duas"
    if not c["obs"] and rng.random() < 0.12:
        return f"{apelido} {c['qtd']}"  # quantidade DEPOIS do produto: "linguiça 2"
    if c["grupo"] == "espetinhos" and " " not in apelido and rng.random() < 0.4:
        apelido = f"de {apelido}"  # "2 de carne", "1 de coalho"
    if c["obs"] == "caprichar":
        if c["qtd"] == 1:  # sem número na frase: o gabarito é qtd=1
            return rng.choice([f"capricha na {apelido}", f"1 {apelido} capricha", f"{apelido} bem caprichada"])
        return f"{num} {apelido} capricha"
    frase = f"{num} {apelido}"
    if c["obs"]:
        obs = c["obs"]
        if obs in ("bem passado", "mal passado") and rng.random() < 0.4:
            obs = obs[:-1] + "a"  # "carne bem passada": o gabarito continua "bem passado"
        frase += f" {obs}"
    return frase


def acabamento(msg: str, rng: random.Random) -> str:
    """Passos finais iguais para qualquer mensagem: caixa baixa, abreviações e erros de digitação."""
    if rng.random() < 0.7:
        msg = msg.lower()
    for longo, curto in ABREV.items():
        if longo in msg and rng.random() < 0.6:
            msg = msg.replace(longo, curto)
    return digitar_errado(msg, rng, taxa=rng.choice([0.0, 0.0, 0.05, 0.1]))


def escrever_mensagem(pedido: Pedido, crus: list[dict], rng: random.Random, ctx: dict) -> str:
    itens = [escrever_item(c, rng) for c in crus if not c.get("cada")]
    cadas = [c for c in crus if c.get("cada")]
    if cadas:
        n = rng.choice(NUM_PALAVRA[cadas[0]["qtd"]])
        nomes = (["espetinho", "tipo de espetinho", "espeto"] if ctx["grupo_cada"] == "espetinhos"
                 else ["acompanhamento", "tipo de acompanhamento", "acompanhamento que vcs têm"])
        itens.insert(0, f"{n} de cada " + rng.choice(nomes))
    fora = ctx["fora"]
    if fora and ctx["modo_fora"] == "pedido":  # pede algo que não existe, no meio do pedido
        itens.insert(rng.randrange(len(itens) + 1), f"{rng.choice(['1', '2', 'um', 'duas'])} {fora[0]}")
    corpo = itens[0]
    for it in itens[1:]:
        corpo += rng.choice(LIGACOES) + it
    frase = f"{rng.choice(ABERTURAS)} {corpo}"
    partes = [rng.choice(SAUDACOES)]
    if fora and ctx["modo_fora"] == "pergunta":
        partes.append(rng.choice([f"vcs tem {' e '.join(fora)}?", f"tem {fora[0]}?",
                                  f"ae vcs tem {' ou '.join(fora)}?"]))
    elif fora and ctx["modo_fora"] == "condicional":
        frase = f"tem {fora[0]}? {rng.choice(['se n tiver', 'se nao tiver', 'se não tiver', 'senao'])} {frase}"
    partes.append(frase)
    if pedido.endereco:
        # Marcador com dígito: digitar_errado não mexe em palavras com número. O endereço real entra no
        # final, para o cliente "digitar" o endereço certo (o gabarito é a cópia literal dele).
        partes.append(rng.choice(["entregar na ", "entrega na ", "endereço: ", "manda na "]) + MARCADOR_END)
    if pedido.pagamento:
        partes.append(rng.choice(PAGAMENTOS[pedido.pagamento]))
    if rng.random() < 0.25:
        partes.insert(rng.choice([1, len(partes)]), rng.choice(RUIDOS))
    partes.append(rng.choice(FECHAMENTOS))
    sep = rng.choice([" ", ", ", ". ", "\n"])
    msg = acabamento(sep.join(p for p in partes if p), rng)
    return msg.replace(MARCADOR_END, pedido.endereco) if pedido.endereco else msg


def mensagem_sem_pedido(cardapio: dict, rng: random.Random) -> str:
    """Mensagem que NÃO é pedido (pergunta, saudação, reclamação): a resposta correta é itens vazio."""
    nomes = [p["produto"] for g in ("espetinhos", "acompanhamentos", "bebidas") for p in cardapio[g]]
    perguntas = [rng.choice(PERGUNTAS).format(p=rng.choice(nomes))]
    if rng.random() < 0.3:
        perguntas.append(rng.choice(PERGUNTAS).format(p=rng.choice(nomes)))
    partes = [rng.choice(SAUDACOES)] + perguntas + [rng.choice(FECHAMENTOS)]
    return acabamento(rng.choice([" ", ", ", ". ", "\n"]).join(p for p in partes if p), rng)


def gerar(n: int, seed: int, proibidas: frozenset = frozenset()) -> list[dict]:
    """proibidas: mensagens que não podem aparecer (ex.: as do teste, para não vazar para o treino)."""
    rng = random.Random(seed)
    cardapio = carregar_cardapio()
    vistos, exemplos = set(proibidas), []
    while len(exemplos) < n:
        if rng.random() < 0.08:
            pedido = Pedido(itens=[], endereco=None, pagamento=None)
            msg = mensagem_sem_pedido(cardapio, rng)
        else:
            pedido, crus, ctx = sortear_pedido(cardapio, rng)
            msg = escrever_mensagem(pedido, crus, rng, ctx)
        if msg in vistos:  # sem mensagens repetidas: evita "decorar" e vazamento entre treino e teste
            continue
        vistos.add(msg)
        exemplos.append({"mensagem": msg, "pedido": pedido.model_dump()})
    return exemplos


def salvar(nome: str, exemplos: list[dict]) -> None:
    with open(DATA_DIR / nome, "w", encoding="utf-8") as f:
        for e in exemplos:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000, help="total de exemplos (treino+val+teste)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--manter-teste", action="store_true",
                    help="não mexe em test.jsonl; --n passa a ser só treino+val (100 de val)")
    a = ap.parse_args()
    if a.manter_teste:
        teste = [json.loads(l)["mensagem"] for l in (DATA_DIR / "test.jsonl").read_text(encoding="utf-8").splitlines()]
        todos = gerar(a.n + 100, a.seed + 1, frozenset(teste))
        salvar("val.jsonl", todos[:100])
        salvar("train.jsonl", todos[100:])
        print(f"treino={a.n} val=100 teste=mantido ({len(teste)})")
    else:
        todos = gerar(a.n, a.seed)
        n_test, n_val = 100, max(50, a.n // 10)
        salvar("test.jsonl", todos[:n_test])
        salvar("val.jsonl", todos[n_test:n_test + n_val])
        salvar("train.jsonl", todos[n_test + n_val:])
        print(f"treino={a.n - n_test - n_val} val={n_val} teste={n_test}")
