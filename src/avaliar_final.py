"""PROVA FINAL: 20 mensagens novas (data/mensagens_finais.txt) com gabarito escrito ANTES de rodar (data/final_gold.jsonl).

Diferença para o resto do projeto: aqui "sem pedido" (itens vazio) é uma resposta válida, porque 3 das 20 mensagens
não são pedidos. O schema do projeto não é alterado; este script usa um modelo Pydantic próprio, mais permissivo.

Compara: Qwen+LoRA v2, Claude Haiku sem regras e Claude Haiku com regras.
Uso: python src/avaliar_final.py
"""
import argparse
import json
from pathlib import Path
from typing import Optional

import anthropic
import torch
from peft import PeftModel
from pydantic import BaseModel, ValidationError
from transformers import AutoModelForCausalLM, AutoTokenizer

from avaliar import _itens, _norm, carregar_jsonl, extrair_json
from env import carregar_env
from mostrar_divergencias import resumo
from prompt import mensagens_curtas, system_prompt
from schema import Item, Pagamento

RAIZ = Path(__file__).resolve().parent.parent
MODELO = "Qwen/Qwen2.5-1.5B-Instruct"
SAIDA = RAIZ / "outputs" / "resultados"


class PedidoFinal(BaseModel):
    itens: list[Item]  # pode ser vazio: "sem pedido"
    endereco: Optional[str] = None
    pagamento: Optional[Pagamento] = None


def parse(texto: str) -> Optional[PedidoFinal]:
    try:
        return PedidoFinal.model_validate_json(extrair_json(texto))
    except ValidationError:
        return None


def igual(a: PedidoFinal, b: PedidoFinal) -> bool:
    return (_itens(a, True) == _itens(b, True) and _norm(a.endereco) == _norm(b.endereco)
            and a.pagamento == b.pagamento)


def ler_mensagens(arquivo: Path) -> list[str]:
    linhas = arquivo.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in linhas if l.strip() and not l.strip().startswith("#")]


def rodar_claude(msgs: list[str], com_regras: bool) -> list[str]:
    client = anthropic.Anthropic()
    sistema = system_prompt(com_regras=com_regras)
    saidas = []
    for m in msgs:
        r = client.messages.create(model="claude-haiku-5-5", max_tokens=2000, system=sistema,
                                   messages=[{"role": "user", "content": m}])
        saidas.append("".join(b.text for b in r.content if b.type == "text"))
    return saidas


def rodar_lora(msgs: list[str], adapter: str) -> list[str]:
    tok = AutoTokenizer.from_pretrained(MODELO)
    base = AutoModelForCausalLM.from_pretrained(MODELO, dtype=torch.bfloat16).to("cuda")
    model = PeftModel.from_pretrained(base, adapter).merge_and_unload().eval()
    saidas = []
    for m in msgs:
        ids = tok.apply_chat_template(mensagens_curtas(m), add_generation_prompt=True, return_tensors="pt",
                                      return_dict=True).to("cuda")
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=300, do_sample=False)
        saidas.append(tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True))
    return saidas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mensagens", default=str(RAIZ / "data" / "mensagens_finais.txt"))
    ap.add_argument("--gold", default=str(RAIZ / "data" / "final_gold.jsonl"))
    ap.add_argument("--nome", default="final", help="prefixo dos arquivos de saída em outputs/resultados")
    ap.add_argument("--rotulo", default="lora_v3", help="nome do adapter no relatório")
    ap.add_argument("--adapter", default=str(RAIZ / "outputs" / "lora-qwen1.5b"))
    ap.add_argument("--sem-claude", action="store_true", help="só o adapter (sem chamar a API: sem custo)")
    a = ap.parse_args()

    carregar_env()
    msgs = ler_mensagens(Path(a.mensagens))
    gold = carregar_jsonl(Path(a.gold))
    assert len(msgs) == len(gold), (len(msgs), len(gold))
    n = len(msgs)
    sem_pedido = [i for i, g in enumerate(gold) if not g["pedido"]["itens"]]

    respostas = {a.rotulo: rodar_lora(msgs, a.adapter)}
    if not a.sem_claude:
        respostas["claude_sem_regras"] = rodar_claude(msgs, False)
        respostas["claude_com_regras"] = rodar_claude(msgs, True)

    resumo_final, detalhes = {}, []
    for nome, brutas in respostas.items():
        ok_total = ok_com = ok_sem = validos = 0
        for i, (m, b, g) in enumerate(zip(msgs, brutas, gold)):
            pred = parse(b)
            gold_p = PedidoFinal.model_validate(g["pedido"])
            alts = [gold_p] + ([PedidoFinal.model_validate(g["pedido_alt"])] if "pedido_alt" in g else [])
            acertou = pred is not None and any(igual(pred, a) for a in alts)
            validos += pred is not None
            ok_total += acertou
            if i in sem_pedido:
                ok_sem += acertou
            else:
                ok_com += acertou
            if not acertou:
                detalhes.append({"modelo": nome, "n": g["n"], "mensagem": m, "nota": g.get("nota"),
                                 "esperado": resumo(gold_p), "obtido": resumo(pred) if pred else "JSON INVALIDO"})
        resumo_final[nome] = {"acerto_exato": f"{ok_total}/{n}", "com_pedido": f"{ok_com}/{n - len(sem_pedido)}",
                              "sem_pedido": f"{ok_sem}/{len(sem_pedido)}", "json_valido": f"{validos}/{n}"}

    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / f"{a.nome}_prova.json").write_text(json.dumps({"resumo": resumo_final, "erros": detalhes},
                                                            ensure_ascii=False, indent=2), encoding="utf-8")
    (SAIDA / f"{a.nome}_respostas.jsonl").write_text("\n".join(
        json.dumps({"n": g["n"], "mensagem": m, **{k: v[i] for k, v in respostas.items()}}, ensure_ascii=False)
        for i, (m, g) in enumerate(zip(msgs, gold))), encoding="utf-8")
    print(json.dumps(resumo_final, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
