"""Gera "prints de terminal" (PNG) com a saída REAL dos comandos do projeto, já limpa de dados sensíveis.

Por que não tirar print de tela: a tela mostra o usuário do Windows, outras janelas e o .env.
Aqui o texto vem direto da execução e passa por limpar() antes de virar imagem.

Uso: python src/gerar_prints.py [--reais outputs/resultados/reais_comparacao_v1.jsonl --sufixo v1]
"""
import argparse
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from avaliar import carregar_jsonl, pedidos_iguais
from mostrar_divergencias import resumo
from schema import parse_saida_do_modelo

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "docs" / "evidencias"
RES = RAIZ / "outputs" / "resultados"

BG, FG, DIM = "#1e1f26", "#e6e6e6", "#8b8fa3"
VERDE, VERMELHO, AMARELO = "#7bd88f", "#ff7b7b", "#f2c94c"


def limpar(texto: str) -> str:
    """Remove o que não pode aparecer num print público: chaves, e-mails e caminhos do computador."""
    texto = re.sub(r"sk-[A-Za-z0-9_\-]{10,}", "[REDIGIDO]", texto)
    texto = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email]", texto)
    texto = texto.replace(str(RAIZ), "projeto").replace(str(Path.home()), "~")
    texto = re.sub(r"[A-Za-z]:\\Users\\[^\\\s]+", "~", texto)
    return texto


def cor_da_linha(linha: str) -> str:
    if linha.startswith("$"):
        return AMARELO
    if re.search(r"passed|OK|válido|✔", linha):
        return VERDE
    if re.search(r"INVALIDO|failed|erro|ERRO", linha):
        return VERMELHO
    if linha.startswith("#") or linha.startswith("  "):
        return FG
    return FG


def cartao(titulo: str, linhas: list[str], arquivo: str, largura_car: int = 118) -> None:
    quebradas = []
    for l in linhas:
        l = limpar(l)
        quebradas += textwrap.wrap(l, largura_car, subsequent_indent="      ") or [""]
    altura = 0.9 + 0.19 * len(quebradas)
    fig = plt.figure(figsize=(11.5, altura), facecolor=BG)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_facecolor(BG)
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, altura)
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        ax.plot(0.02 + i * 0.018, altura - 0.3, "o", color=c, markersize=8)
    ax.text(0.5, altura - 0.3, titulo, color=DIM, ha="center", va="center", fontsize=10)
    y = altura - 0.75
    for l in quebradas:
        ax.text(0.02, y, l, color=cor_da_linha(l), family="monospace", fontsize=9, va="center")
        y -= 0.19
    SAIDA.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA / arquivo, dpi=140, facecolor=BG)
    plt.close(fig)
    print("salvo:", arquivo)


def print_testes() -> None:
    r = subprocess.run([sys.executable, "-W", "ignore", "-m", "pytest", "tests", "-q", "--no-header", "-p", "no:warnings"],
                       cwd=RAIZ, capture_output=True, text=True, encoding="utf-8")
    saida = [l for l in r.stdout.splitlines() if l.strip()]
    cartao("terminal — testes automáticos", ["$ pytest tests -q"] + saida, "02_terminal_testes.png")


def print_erros(arquivo_reais: Path, sufixo: str) -> None:
    linhas = carregar_jsonl(arquivo_reais)
    out = [f"$ python src/mostrar_divergencias.py   # modelo {sufixo} vs Claude, mensagens escritas à mão", ""]
    concordam = 0
    for n, l in enumerate(linhas, 1):
        c, m = parse_saida_do_modelo(l["claude"]), parse_saida_do_modelo(l["lora"])
        if c is not None and m is not None and pedidos_iguais(c, m):
            concordam += 1
            continue
        out += [f"#{n} {l['mensagem']}", f"  CLAUDE: {resumo(c)}", f"  MODELO: {resumo(m)}", ""]
    out.append(f"concordam: {concordam}/{len(linhas)}")
    cartao(f"terminal — onde o modelo {sufixo} errou (mensagens reais)", out, f"03_erros_modelo_{sufixo}.png")


def print_resultados() -> None:
    out = ["$ cat outputs/resultados/*.json   # resumo", ""]
    out.append(f"{'modelo':<26}{'JSON válido':>12}{'acerto exato':>14}{'latência':>10}")
    for arq, nome in [("baseline_base", "Qwen 1.5B sem treino"), ("lora_qwen_v1", "Qwen + LoRA v1"),
                      ("lora_qwen_v2", "Qwen + LoRA v2"), ("baseline_claude", "Claude Haiku 5.5 (API)"),
                      ("baseline_claude_regras", "Claude Haiku 5.5 + regras")]:
        p = RES / f"{arq}.json"
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            out.append(f"{nome:<26}{d['json_valido']*100:>11.0f}%{d['acerto_exato']*100:>13.0f}%{d['latencia_media_s']:>9.1f}s")
    cartao("terminal — resultados nas 100 mensagens de teste", out, "04_terminal_resultados.png")


def print_final() -> None:
    """Principais erros do modelo na prova final (mensagens novas)."""
    caminho = RES / "final_prova.json"
    if not caminho.exists():
        return
    erros = [e for e in json.loads(caminho.read_text(encoding="utf-8"))["erros"]
             if e["modelo"] == "lora_v2" and e["n"] in (2, 3, 7, 13, 14)]
    out = ["$ python src/avaliar_final.py   # prova final, 20 mensagens novas, modelo v2 (6/20)", ""]
    for e in erros:
        out += [f"#{e['n']} {e['mensagem']}", f"  ESPERADO: {e['esperado'] or '(sem pedido)'}",
                f"  OBTIDO  : {e['obtido'] or '(sem pedido)'}", ""]
    cartao("terminal — erros do modelo v2 na prova final", out, "06_erros_prova_final.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reais", default=str(RES / "reais_comparacao_v1.jsonl"))
    ap.add_argument("--sufixo", default="v1")
    a = ap.parse_args()
    print_testes()
    print_erros(Path(a.reais), a.sufixo)
    print_resultados()
    print_final()
