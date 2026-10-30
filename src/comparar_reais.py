"""Passa as mensagens REAIS (data/mensagens_reais.txt) pelo modelo treinado e pelo Claude e guarda os dois resultados.

Não há gabarito para essas mensagens: o objetivo é ver ONDE os dois divergem, para o humano decidir
quem tem razão e assim montar um gabarito revisado.
Uso: python src/comparar_reais.py
"""
import json
import time
from pathlib import Path

import anthropic
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from avaliar import extrair_json
from env import carregar_env
from prompt import mensagens_curtas, system_prompt

RAIZ = Path(__file__).resolve().parent.parent
MODELO = "Qwen/Qwen2.5-1.5B-Instruct"
SAIDA = RAIZ / "outputs" / "resultados" / "reais_comparacao.jsonl"


def ler_mensagens() -> list[str]:
    linhas = (RAIZ / "data" / "mensagens_reais.txt").read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in linhas if l.strip() and not l.strip().startswith("#")]


def main() -> None:
    msgs = ler_mensagens()
    print(len(msgs), "mensagens")

    carregar_env()
    client = anthropic.Anthropic()
    claude = []
    for m in msgs:
        r = client.messages.create(model="claude-haiku-5-5", max_tokens=2000, system=system_prompt(),
                                   messages=[{"role": "user", "content": m}])
        claude.append(extrair_json("".join(b.text for b in r.content if b.type == "text")))
    print("claude ok")

    tok = AutoTokenizer.from_pretrained(MODELO)
    base = AutoModelForCausalLM.from_pretrained(MODELO, dtype=torch.bfloat16).to("cuda")
    model = PeftModel.from_pretrained(base, str(RAIZ / "outputs" / "lora-qwen1.5b")).merge_and_unload().eval()
    lora = []
    for m in msgs:
        ids = tok.apply_chat_template(mensagens_curtas(m), add_generation_prompt=True, return_tensors="pt",
                                      return_dict=True).to("cuda")
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=300, do_sample=False)
        lora.append(extrair_json(tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)))

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text("\n".join(json.dumps({"mensagem": m, "claude": c, "lora": l}, ensure_ascii=False)
                               for m, c, l in zip(msgs, claude, lora)), encoding="utf-8")
    print("salvo em", SAIDA)


if __name__ == "__main__":
    main()
