"""Métricas de avaliação, iguais para qualquer modelo (base, fine-tunado ou Claude).

Métricas da tabela do README:
- json_valido: % de respostas que viram um Pedido válido (schema.py).
- acerto_exato: % de respostas cujo pedido inteiro é IGUAL ao gabarito.
- f1_*: F1 por campo, calculado sobre todos os itens do conjunto de teste.
- latência e custo: medidos por quem gera as respostas (scripts de baseline/avaliação).
"""
import json
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Optional

from schema import Pedido, parse_saida_do_modelo

RESULTADOS_DIR = Path(__file__).resolve().parent.parent / "outputs" / "resultados"


def carregar_jsonl(caminho: Path) -> list[dict]:
    return [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]


def extrair_json(texto: str) -> str:
    """Tira cercas de markdown e texto em volta, igual para todos os modelos (comparação justa)."""
    texto = re.sub(r"```(?:json)?", "", texto).strip()
    ini, fim = texto.find("{"), texto.rfind("}")
    return texto[ini:fim + 1] if ini != -1 and fim > ini else texto


def _norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = " ".join(s.lower().replace(".", "").split())  # "Av. Brasil" e "av brasil" são o mesmo endereço
    return s or None


def _itens(p: Pedido, com_obs: bool) -> Counter:
    return Counter((i.produto.lower(), i.qtd) + ((_norm(i.obs),) if com_obs else ()) for i in p.itens)


def _f1(acertos: int, previstos: int, esperados: int) -> float:
    if previstos == 0 or esperados == 0 or acertos == 0:
        return 0.0
    p, r = acertos / previstos, acertos / esperados
    return 2 * p * r / (p + r)


def pedidos_iguais(a: Pedido, b: Pedido) -> bool:
    return (_itens(a, True) == _itens(b, True) and _norm(a.endereco) == _norm(b.endereco)
            and a.pagamento == b.pagamento)


def calcular_metricas(brutas: list[str], gabaritos: list[dict]) -> dict:
    """brutas: texto que o modelo respondeu; gabaritos: dicts de pedido corretos (mesma ordem)."""
    n = len(gabaritos)
    validos = exatos = 0
    ac_item = ac_item_obs = prev_item = esp_item = 0
    ac_end = ac_pag = 0
    for texto, gold_d in zip(brutas, gabaritos):
        gold = Pedido.model_validate(gold_d)
        esp_item += len(gold.itens)
        pred = parse_saida_do_modelo(extrair_json(texto))
        if pred is None:
            continue
        validos += 1
        prev_item += len(pred.itens)
        ac_item += sum((_itens(pred, False) & _itens(gold, False)).values())
        ac_item_obs += sum((_itens(pred, True) & _itens(gold, True)).values())
        exatos += pedidos_iguais(pred, gold)
        ac_end += _norm(pred.endereco) == _norm(gold.endereco)
        ac_pag += pred.pagamento == gold.pagamento
    return {
        "n": n,
        "json_valido": validos / n,
        "acerto_exato": exatos / n,
        "f1_produto_qtd": _f1(ac_item, prev_item, esp_item),
        "f1_produto_qtd_obs": _f1(ac_item_obs, prev_item, esp_item),
        "acc_endereco": ac_end / n,  # sobre todos os exemplos; inválido conta como erro
        "acc_pagamento": ac_pag / n,
    }


def resumir_latencia(segundos: list[float]) -> dict:
    s = sorted(segundos)
    return {"latencia_media_s": statistics.mean(s), "latencia_p95_s": s[int(0.95 * (len(s) - 1))]}


def salvar_resultado(nome: str, metricas: dict, extra: dict) -> Path:
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    caminho = RESULTADOS_DIR / f"{nome}.json"
    caminho.write_text(json.dumps({**metricas, **extra}, ensure_ascii=False, indent=2), encoding="utf-8")
    return caminho
