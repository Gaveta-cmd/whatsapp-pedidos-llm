"""Avalia o modelo ajustado (base + adapter LoRA) no conjunto de teste, com as mesmas métricas dos baselines.

Uso: python src/avaliar_modelo.py --adapter outputs/lora-qwen1.5b --nome lora_qwen
"""
import argparse
import json
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from avaliar import RESULTADOS_DIR, calcular_metricas, carregar_jsonl, resumir_latencia, salvar_resultado
from prompt import mensagens_curtas

RAIZ = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--adapter", default=str(RAIZ / "outputs" / "lora-qwen1.5b"))
    ap.add_argument("--nome", default="lora_qwen")
    ap.add_argument("--n", type=int, default=None)
    a = ap.parse_args()

    teste = carregar_jsonl(RAIZ / "data" / "test.jsonl")[: a.n]
    tok = AutoTokenizer.from_pretrained(a.modelo)
    base = AutoModelForCausalLM.from_pretrained(a.modelo, dtype=torch.bfloat16).to("cuda")
    model = PeftModel.from_pretrained(base, a.adapter).merge_and_unload().eval()  # cola o adapter no modelo

    # aquecimento: a primeira geração na placa é lenta e não deve entrar na medida de latência
    w = tok.apply_chat_template(mensagens_curtas("oi"), add_generation_prompt=True, return_tensors="pt",
                                return_dict=True).to("cuda")
    model.generate(**w, max_new_tokens=8, do_sample=False)

    brutas, tempos = [], []
    for i, ex in enumerate(teste, 1):
        ids = tok.apply_chat_template(mensagens_curtas(ex["mensagem"]), add_generation_prompt=True,
                                      return_tensors="pt", return_dict=True).to("cuda")
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=300, do_sample=False)
        torch.cuda.synchronize()
        tempos.append(time.perf_counter() - t0)
        brutas.append(tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True))
        if i % 20 == 0:
            print(f"{i}/{len(teste)}")

    metricas = calcular_metricas(brutas, [e["pedido"] for e in teste])
    adapter = Path(a.adapter)
    adapter_txt = adapter.relative_to(RAIZ).as_posix() if adapter.is_relative_to(RAIZ) else adapter.name  # sem caminho do PC
    extra = {"modelo": a.modelo, "adapter": adapter_txt, **resumir_latencia(tempos),
             "gpu": torch.cuda.get_device_name(0)}
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTADOS_DIR / f"pred_{a.nome}.jsonl").write_text(
        "\n".join(json.dumps({"mensagem": e["mensagem"], "resposta": b}, ensure_ascii=False)
                  for e, b in zip(teste, brutas)), encoding="utf-8")
    print(salvar_resultado(a.nome, metricas, extra))
    print(json.dumps({**metricas, **extra}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
