"""API do extrator de pedidos: POST /extrair-pedido recebe a mensagem do cliente e devolve o pedido em JSON.

Uso (da raiz do projeto):
    uvicorn --app-dir src api:app --port 8000
Variável opcional ADAPTER: pasta do adapter LoRA (padrão: outputs/lora-qwen1.5b). O modelo carrega na 1ª chamada.
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError

from avaliar import extrair_json
from prompt import mensagens_curtas
from schema import Item, Pagamento

RAIZ = Path(__file__).resolve().parent.parent
MODELO = "Qwen/Qwen2.5-1.5B-Instruct"

app = FastAPI(title="Extrator de pedidos de WhatsApp", version="1.0")


class Mensagem(BaseModel):
    mensagem: str = Field(min_length=1, max_length=1000)


class PedidoExtraido(BaseModel):
    itens: list[Item]  # lista vazia = a mensagem não é um pedido
    endereco: Optional[str] = None
    pagamento: Optional[Pagamento] = None


@lru_cache(maxsize=1)
def _carregar():
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    adapter = os.environ.get("ADAPTER", str(RAIZ / "outputs" / "lora-qwen1.5b"))
    tok = AutoTokenizer.from_pretrained(MODELO)
    base = AutoModelForCausalLM.from_pretrained(MODELO, dtype=torch.bfloat16).to("cuda")
    return tok, PeftModel.from_pretrained(base, adapter).merge_and_unload().eval()


def gerar_texto(mensagem: str) -> str:
    """Resposta bruta do modelo ajustado (separada para poder ser trocada nos testes)."""
    import torch

    tok, model = _carregar()
    ids = tok.apply_chat_template(mensagens_curtas(mensagem), add_generation_prompt=True, return_tensors="pt",
                                  return_dict=True).to("cuda")
    with torch.no_grad():
        out = model.generate(**ids, max_new_tokens=300, do_sample=False)
    return tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)


@app.get("/saude")
def saude() -> dict:
    return {"status": "ok"}


@app.post("/extrair-pedido", response_model=PedidoExtraido)
def extrair_pedido(corpo: Mensagem) -> PedidoExtraido:
    bruto = gerar_texto(corpo.mensagem)
    try:
        return PedidoExtraido.model_validate_json(extrair_json(bruto))
    except (ValidationError, ValueError):
        raise HTTPException(status_code=502, detail="O modelo não devolveu um pedido válido.")
