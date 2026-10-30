"""Baseline 2: o Claude via API responde a mesma prova (conjunto de teste).

Uso:
  set ANTHROPIC_API_KEY=...   (você define; o script só lê da variável de ambiente)
  python src/baseline_claude.py --modelo claude-haiku-5-5 --preco-in 1.0 --preco-out 5.0

--preco-in / --preco-out: dólares por 1 MILHÃO de tokens (confira na página de preços da Anthropic).
Sem eles, o script salva só os tokens usados e não calcula custo (não chutamos preço).
"""
import argparse
import json
import time
from pathlib import Path

import anthropic

from avaliar import RESULTADOS_DIR, calcular_metricas, carregar_jsonl, resumir_latencia, salvar_resultado
from env import carregar_env
from prompt import system_prompt

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="claude-haiku-5-5")
    ap.add_argument("--n", type=int, default=None, help="usar só os N primeiros (para testar barato)")
    ap.add_argument("--regras", action="store_true", help="inclui as regras de negócio no prompt do Claude")
    ap.add_argument("--preco-in", type=float, default=None)
    ap.add_argument("--preco-out", type=float, default=None)
    a = ap.parse_args()

    teste = carregar_jsonl(DATA_DIR / "test.jsonl")[: a.n]
    carregar_env()  # lê o .env da raiz, se existir
    client = anthropic.Anthropic()  # lê ANTHROPIC_API_KEY do ambiente
    sistema = system_prompt(com_regras=a.regras)
    nome = "baseline_claude_regras" if a.regras else "baseline_claude"

    brutas, tempos, tok_in, tok_out, paradas = [], [], 0, 0, {}
    for i, ex in enumerate(teste, 1):
        t0 = time.perf_counter()
        r = client.messages.create(
            model=a.modelo, max_tokens=2000, system=sistema,
            messages=[{"role": "user", "content": ex["mensagem"]}],
        )
        tempos.append(time.perf_counter() - t0)
        brutas.append("".join(b.text for b in r.content if b.type == "text"))
        tok_in += r.usage.input_tokens
        tok_out += r.usage.output_tokens
        paradas[r.stop_reason] = paradas.get(r.stop_reason, 0) + 1  # por que o modelo parou de escrever
        if i % 10 == 0:
            print(f"{i}/{len(teste)}")

    metricas = calcular_metricas(brutas, [e["pedido"] for e in teste])
    extra = {"modelo": a.modelo, **resumir_latencia(tempos),
             "tokens_entrada_total": tok_in, "tokens_saida_total": tok_out, "motivos_de_parada": paradas}
    if a.preco_in is not None and a.preco_out is not None:
        custo = tok_in / 1e6 * a.preco_in + tok_out / 1e6 * a.preco_out
        extra["custo_por_1000_msgs_usd"] = custo / len(teste) * 1000

    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTADOS_DIR / f"pred_{nome}.jsonl").write_text(
        "\n".join(json.dumps({"mensagem": e["mensagem"], "resposta": b}, ensure_ascii=False)
                  for e, b in zip(teste, brutas)), encoding="utf-8")
    print(salvar_resultado(nome, metricas, extra))
    print(json.dumps({**metricas, **extra}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
