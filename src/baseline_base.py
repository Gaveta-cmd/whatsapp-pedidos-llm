"""Baseline 1: o modelo pequeno SEM treino responde a mesma prova, na sua GPU.

Uso: python src/baseline_base.py --modelo Qwen/Qwen2.5-1.5B-Instruct
Decodificação gulosa (do_sample=False): sempre a mesma resposta, resultado reprodutível.
"""
import argparse
import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from avaliar import RESULTADOS_DIR, calcular_metricas, carregar_jsonl, resumir_latencia, salvar_resultado
from prompt import system_prompt

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--nome", default="baseline_base")
    a = ap.parse_args()

    teste = carregar_jsonl(DATA_DIR / "test.jsonl")[: a.n]
    tok = AutoTokenizer.from_pretrained(a.modelo)
    model = AutoModelForCausalLM.from_pretrained(a.modelo, dtype=torch.bfloat16).to("cuda").eval()
    sistema = system_prompt()

    brutas, tempos = [], []
    for i, ex in enumerate(teste, 1):
        msgs = [{"role": "system", "content": sistema}, {"role": "user", "content": ex["mensagem"]}]
        ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt",
                                      return_dict=True).to("cuda")
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=300, do_sample=False)
        torch.cuda.synchronize()
        tempos.append(time.perf_counter() - t0)
        brutas.append(tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True))
        if i % 10 == 0:
            print(f"{i}/{len(teste)}")

    metricas = calcular_metricas(brutas, [e["pedido"] for e in teste])
    extra = {"modelo": a.modelo, **resumir_latencia(tempos), "gpu": torch.cuda.get_device_name(0)}

    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTADOS_DIR / f"pred_{a.nome}.jsonl").write_text(
        "\n".join(json.dumps({"mensagem": e["mensagem"], "resposta": b}, ensure_ascii=False)
                  for e, b in zip(teste, brutas)), encoding="utf-8")
    print(salvar_resultado(a.nome, metricas, extra))
    print(json.dumps({**metricas, **extra}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
