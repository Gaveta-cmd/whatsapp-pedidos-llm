"""Teste de robustez à pontuação e às maiúsculas (critério de aceitação do v4).

Passa as 40 mensagens de desenvolvimento pelo modelo em 4 formas (original, minúsculas, sem pontuação, ambos) e
mede a concordância com as respostas do Claude guardadas em outputs/resultados/reais_claude_ref.jsonl.

CRITÉRIO (fixado ANTES de ver os resultados do v4):
  aprovado se, nas 4 formas, a concordância for >= 34/40 E a diferença entre a melhor e a pior forma for <= 3.
  (o v2 passaria, com 35 a 37; o v3 não passa, com 24 a 36)

Uso: python src/robustez.py --adapter outputs/lora-qwen1.5b --nome v4
"""
import argparse
import json
import re
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from avaliar import RESULTADOS_DIR, carregar_jsonl, extrair_json, pedidos_iguais
from prompt import mensagens_curtas
from schema import parse_saida_do_modelo

RAIZ = Path(__file__).resolve().parent.parent
MODELO = "Qwen/Qwen2.5-1.5B-Instruct"
MINIMO, DIFERENCA_MAXIMA = 34, 3


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default=str(RAIZ / "outputs" / "lora-qwen1.5b"))
    ap.add_argument("--nome", default="v4")
    a = ap.parse_args()

    ref = carregar_jsonl(RESULTADOS_DIR / "reais_claude_ref.jsonl")
    msgs = [l["mensagem"] for l in ref]
    claude = [parse_saida_do_modelo(extrair_json(l["claude"])) for l in ref]
    formas = {
        "original": msgs,
        "minusculas": [m.lower() for m in msgs],
        "sem pontuacao": [re.sub(r"[.,?!]+", " ", m) for m in msgs],
        "minusculas e sem pontuacao": [re.sub(r"[.,?!]+", " ", m.lower()) for m in msgs],
    }

    tok = AutoTokenizer.from_pretrained(MODELO)
    base = AutoModelForCausalLM.from_pretrained(MODELO, dtype=torch.bfloat16).to("cuda")
    model = PeftModel.from_pretrained(base, a.adapter).merge_and_unload().eval()

    resultado = {}
    for nome, textos in formas.items():
        acertos = 0
        for t, c in zip(textos, claude):
            ids = tok.apply_chat_template(mensagens_curtas(t), add_generation_prompt=True, return_tensors="pt",
                                          return_dict=True).to("cuda")
            with torch.no_grad():
                out = model.generate(**ids, max_new_tokens=300, do_sample=False)
            p = parse_saida_do_modelo(extrair_json(tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)))
            acertos += c is not None and p is not None and pedidos_iguais(c, p)
        resultado[nome] = acertos
        print(f"{nome:28} {acertos}/40", flush=True)

    pior, melhor = min(resultado.values()), max(resultado.values())
    aprovado = pior >= MINIMO and melhor - pior <= DIFERENCA_MAXIMA
    print(f"pior={pior} melhor={melhor} diferenca={melhor - pior} -> {'APROVADO' if aprovado else 'REPROVADO'}")
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTADOS_DIR / f"robustez_{a.nome}.json").write_text(json.dumps(
        {"concordancia_com_claude_de_40": resultado, "criterio": f">= {MINIMO} em todas e diferenca <= {DIFERENCA_MAXIMA}",
         "aprovado": bool(aprovado)}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
