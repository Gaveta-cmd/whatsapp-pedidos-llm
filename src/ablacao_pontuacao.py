"""Qual SINAL de pontuação faz o modelo perder itens? Tira um tipo de cada vez das 40 mensagens de desenvolvimento
e conta em quantas os ITENS (produto, qtd) ficam iguais aos do Claude.
Uso: python src/ablacao_pontuacao.py --adapter outputs/lora-qwen1.5b-v3 --nome v3
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from avaliar import RESULTADOS_DIR, carregar_jsonl, extrair_json
from prompt import mensagens_curtas
from schema import parse_saida_do_modelo

MODELO = "Qwen/Qwen2.5-1.5B-Instruct"
FORMAS = {
    "original": lambda m: m,
    "sem virgula": lambda m: m.replace(",", " "),
    "sem ponto final/interrogacao": lambda m: re.sub(r"[.?!]+", " ", m),
    "so quebra de frase vira virgula": lambda m: re.sub(r"[.?!]+\s", ", ", m),
    "sem nenhuma": lambda m: re.sub(r"[.,?!]+", " ", m),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--nome", required=True)
    a = ap.parse_args()
    ref = carregar_jsonl(RESULTADOS_DIR / "reais_claude_ref.jsonl")
    claude = [parse_saida_do_modelo(extrair_json(l["claude"])) for l in ref]
    tok = AutoTokenizer.from_pretrained(MODELO)
    base = AutoModelForCausalLM.from_pretrained(MODELO, dtype=torch.bfloat16).to("cuda")
    model = PeftModel.from_pretrained(base, a.adapter).merge_and_unload().eval()
    resultado = {}
    for forma, f in FORMAS.items():
        itens_ok = 0
        for l, c in zip(ref, claude):
            ids = tok.apply_chat_template(mensagens_curtas(f(l["mensagem"])), add_generation_prompt=True,
                                          return_tensors="pt", return_dict=True).to("cuda")
            with torch.no_grad():
                out = model.generate(**ids, max_new_tokens=300, do_sample=False)
            p = parse_saida_do_modelo(extrair_json(tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)))
            if p is not None and c is not None:
                itens_ok += Counter((i.produto.lower(), i.qtd) for i in c.itens) == Counter((i.produto.lower(), i.qtd) for i in p.itens)
        resultado[forma] = itens_ok
        print(f"{a.nome:20} {forma:34} itens exatos {itens_ok}/40", flush=True)
    (RESULTADOS_DIR / f"ablacao_pontuacao_{a.nome}.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
