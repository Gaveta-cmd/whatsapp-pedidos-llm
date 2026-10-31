"""Fine-tuning com LoRA: ensina o Qwen a transformar mensagem de WhatsApp em JSON de pedido.

LoRA em vez de treinar o modelo inteiro: congelamos os ~1,5 bilhão de números do modelo e treinamos só
umas "pecinhas" pequenas (adaptadores) coladas nele. Fica leve, rápido e o resultado é um arquivo
pequeno (o adapter) que se acopla ao modelo base.

Uso: python src/treinar.py --epocas 3
"""
import argparse
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import (AutoModelForCausalLM, AutoTokenizer, DataCollatorForSeq2Seq, Trainer,
                          TrainingArguments)

from avaliar import carregar_jsonl
from prompt import mensagens_curtas, pedido_para_texto

RAIZ = Path(__file__).resolve().parent.parent
DATA_DIR = RAIZ / "data"
SAIDA = RAIZ / "outputs" / "lora-qwen1.5b"


def tokenizar(ex: dict, tok, max_len: int = 512) -> dict:
    """Monta (instrução + resposta). Só a RESPOSTA conta na nota do treino (labels); a instrução vira -100."""
    texto_prompt = tok.apply_chat_template(mensagens_curtas(ex["mensagem"]), tokenize=False,
                                           add_generation_prompt=True)
    prompt_ids = tok(texto_prompt, add_special_tokens=False)["input_ids"]
    resposta_ids = tok(pedido_para_texto(ex["pedido"]) + "<|im_end|>", add_special_tokens=False)["input_ids"]
    ids = (prompt_ids + resposta_ids)[:max_len]
    labels = ([-100] * len(prompt_ids) + resposta_ids)[:max_len]
    return {"input_ids": ids, "attention_mask": [1] * len(ids), "labels": labels}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--epocas", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--acumular", type=int, default=4, help="lote efetivo = batch x acumular")
    ap.add_argument("--retomar", action="store_true", help="continua do último checkpoint em outputs/checkpoints")
    ap.add_argument("--dados", default=str(DATA_DIR), help="pasta com train.jsonl e val.jsonl")
    ap.add_argument("--saida", default=str(SAIDA), help="pasta onde salvar o adapter (checkpoints ficam em <saida>_ckpt)")
    a = ap.parse_args()
    saida = Path(a.saida)
    dados = Path(a.dados)

    tok = AutoTokenizer.from_pretrained(a.modelo)
    model = AutoModelForCausalLM.from_pretrained(a.modelo, dtype=torch.bfloat16).to("cuda")

    lora = LoraConfig(r=a.rank, lora_alpha=2 * a.rank, lora_dropout=0.05, task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    def prep(nome: str) -> Dataset:
        ds = Dataset.from_list(carregar_jsonl(dados / nome))
        return ds.map(lambda ex: tokenizar(ex, tok), remove_columns=ds.column_names)

    treino, val = prep("train.jsonl"), prep("val.jsonl")

    args = TrainingArguments(
        output_dir=str(RAIZ / "outputs" / "checkpoints") if saida == SAIDA else str(saida) + "_ckpt", num_train_epochs=a.epocas, learning_rate=a.lr,
        per_device_train_batch_size=a.batch, per_device_eval_batch_size=a.batch, gradient_accumulation_steps=a.acumular,
        lr_scheduler_type="cosine", warmup_steps=10, bf16=True, logging_steps=5, disable_tqdm=True,
        eval_strategy="epoch",
        save_strategy="steps", save_steps=50, save_total_limit=1,  # checkpoint: dá para pausar
        report_to="none", remove_unused_columns=False, seed=42,
    )
    trainer = Trainer(model=model, args=args, train_dataset=treino, eval_dataset=val,
                      data_collator=DataCollatorForSeq2Seq(tok, padding=True, label_pad_token_id=-100))
    trainer.train(resume_from_checkpoint=True if a.retomar else None)

    saida.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(saida)  # salva só o adapter (pequeno)
    tok.save_pretrained(saida)
    print("adapter salvo em", saida.name)


if __name__ == "__main__":
    main()
