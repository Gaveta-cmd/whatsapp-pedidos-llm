"""Diagnóstico: ONDE um adapter diverge do Claude nas 40 mensagens de desenvolvimento, nas 4 formas de escrita.

Para cada divergência, classifica o tipo (item faltando, item a mais, quantidade, observação, endereço, pagamento,
pedido vs não-pedido) para comparar adapters (v3 x v4) por tipo de erro, não só pelo total.
Uso: python src/diagnosticar.py --adapter outputs/lora-qwen1.5b-v3 --nome v3
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from avaliar import RESULTADOS_DIR, _norm, carregar_jsonl, extrair_json, pedidos_iguais
from prompt import mensagens_curtas
from schema import parse_saida_do_modelo

RAIZ = Path(__file__).resolve().parent.parent
MODELO = "Qwen/Qwen2.5-1.5B-Instruct"


def tipos_de_erro(c, p) -> list[str]:
    """c = Claude (referência), p = modelo avaliado."""
    if p is None:
        return ["json_invalido"]
    if not c.itens and p.itens:
        return ["pedido_onde_nao_ha"]
    if c.itens and not p.itens:
        return ["perdeu_o_pedido_todo"]
    tipos = []
    cp = {i.produto.lower(): i for i in c.itens}
    pp = {i.produto.lower(): i for i in p.itens}
    if set(cp) - set(pp):
        tipos.append("item_faltando")
    if set(pp) - set(cp):
        tipos.append("item_a_mais")
    for prod in set(cp) & set(pp):
        if cp[prod].qtd != pp[prod].qtd:
            tipos.append("quantidade")
        if _norm(cp[prod].obs) != _norm(pp[prod].obs):
            tipos.append("observacao")
    if _norm(c.endereco) != _norm(p.endereco):
        tipos.append("endereco")
    if c.pagamento != p.pagamento:
        tipos.append("pagamento")
    return tipos


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--nome", required=True)
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

    resumo, detalhes = {}, []
    for forma, textos in formas.items():
        erros = Counter()
        acertos = 0
        for i, (t, c) in enumerate(zip(textos, claude)):
            ids = tok.apply_chat_template(mensagens_curtas(t), add_generation_prompt=True, return_tensors="pt",
                                          return_dict=True).to("cuda")
            with torch.no_grad():
                out = model.generate(**ids, max_new_tokens=300, do_sample=False)
            bruto = tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
            p = parse_saida_do_modelo(extrair_json(bruto))
            ok = c is not None and p is not None and pedidos_iguais(c, p)
            acertos += ok
            tipos = [] if ok else tipos_de_erro(c, p)
            erros.update(tipos)
            detalhes.append({"forma": forma, "i": i, "ok": bool(ok), "tipos": tipos, "mensagem": t, "modelo": bruto})
        resumo[forma] = {"acertos": acertos, "erros_por_tipo": dict(erros.most_common())}
        print(forma, acertos, dict(erros.most_common()), flush=True)

    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTADOS_DIR / f"diagnostico_{a.nome}.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    # respostas completas ficam só no computador (outputs/ não vai para o GitHub)
    (RAIZ / "outputs" / f"diagnostico_{a.nome}_detalhes.jsonl").write_text(
        "\n".join(json.dumps(d, ensure_ascii=False) for d in detalhes), encoding="utf-8")


if __name__ == "__main__":
    main()
