"""Gera as imagens de evidência (docs/evidencias/) a partir dos resultados REAIS em outputs/resultados/.

Só lê números dos arquivos de resultado: nenhuma chave, caminho ou dado pessoal entra nas imagens.
Uso: python src/gerar_evidencias.py   (rode de novo a cada marco do projeto)
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "outputs" / "resultados"
SAIDA = RAIZ / "docs" / "evidencias"

# (arquivo, rótulo, cor) na ordem em que aparecem no gráfico; o que não existir ainda é pulado
# Duas fases, cada uma com o SEU teste sintético: nunca misturar resultados de cardápios diferentes.
FASE_C14 = [  # cardápio de 14 itens (v1, v2)
    ("baseline_base_c14", "Qwen 1.5B\nsem treino", "#9aa0a6"),
    ("lora_qwen_v1", "Qwen + LoRA\nv1", "#7aa7e8"),
    ("lora_qwen_v2", "Qwen + LoRA\nv2", "#2f6fdb"),
    ("baseline_claude_c14", "Claude Haiku\n(API)", "#e08a3c"),
    ("baseline_claude_regras_c14", "Claude Haiku\n+ regras", "#c2611b"),
]
FASE_C17 = [  # cardápio de 17 itens (v3 em diante)
    ("baseline_base", "Qwen 1.5B\nsem treino", "#9aa0a6"),
    ("lora_qwen_v3", "Qwen + LoRA\nv3", "#2f6fdb"),
    ("baseline_claude", "Claude Haiku\n(API)", "#e08a3c"),
    ("baseline_claude_regras", "Claude Haiku\n+ regras", "#c2611b"),
]


def carregar(modelos: list) -> list[tuple[str, str, dict]]:
    achados = []
    for arq, rotulo, cor in modelos:
        caminho = RES / f"{arq}.json"
        if caminho.exists():
            achados.append((rotulo, cor, json.loads(caminho.read_text(encoding="utf-8"))))
    return achados


def barras(ax, rotulos, valores, cores, titulo, formato, ymax=None):
    b = ax.bar(rotulos, valores, color=cores)
    ax.set_title(titulo, fontsize=12, fontweight="bold", loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    if ymax:
        ax.set_ylim(0, ymax)
    for r, v in zip(b, valores):
        ax.text(r.get_x() + r.get_width() / 2, r.get_height(), formato(v), ha="center", va="bottom", fontsize=10)


def grafico_final(arquivo: str, chave: str, rotulo: str, saida: str, titulo: str) -> None:
    """Prova final (20 mensagens novas): total, com pedido e sem pedido."""
    caminho = RES / arquivo
    if not caminho.exists():
        return
    r = json.loads(caminho.read_text(encoding="utf-8"))["resumo"]
    sistemas = [(chave, rotulo, "#2f6fdb"), ("claude_sem_regras", "Claude\nsem regras", "#e08a3c"),
                ("claude_com_regras", "Claude\ncom regras", "#c2611b")]

    def pct(txt: str) -> float:
        a, b = txt.split("/")
        return int(a) / int(b) * 100

    rot = [s[1] for s in sistemas]
    cores = [s[2] for s in sistemas]
    fig, eixos = plt.subplots(1, 3, figsize=(14, 4.6))
    barras(eixos[0], rot, [pct(r[s[0]]["acerto_exato"]) for s in sistemas], cores,
           "Acerto exato — 20 mensagens", lambda v: f"{v:.0f}%", 115)
    barras(eixos[1], rot, [pct(r[s[0]]["com_pedido"]) for s in sistemas], cores,
           "Mensagens COM pedido (17)", lambda v: f"{v:.0f}%", 115)
    barras(eixos[2], rot, [pct(r[s[0]]["sem_pedido"]) for s in sistemas], cores,
           "Mensagens SEM pedido (3)", lambda v: f"{v:.0f}%", 115)
    for ax in eixos:
        ax.tick_params(axis="x", labelsize=8)
    fig.suptitle(titulo, fontsize=13, fontweight="bold", x=0.01, ha="left")
    fig.text(0.01, 0.01, "Gabarito escrito antes de rodar os modelos  •  endereço comparado literalmente (critério estrito)",
             fontsize=8, color="#666")
    fig.tight_layout(rect=(0, 0.04, 1, 0.93))
    fig.savefig(SAIDA / saida, dpi=150)
    plt.close(fig)


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    grafico_final("final_prova_v2_c14.json", "lora_v2", "Qwen + LoRA v2", "05_prova_final_v2.png",
                  "Prova final (cardápio de 14 itens): 20 mensagens novas, modelo v2")
    grafico_final("final_v3_prova.json", "lora_v3", "Qwen + LoRA v3", "07_prova_final_v3.png",
                  "Prova final v3 (cardápio de 17 itens): 20 mensagens novas, nunca vistas no treino")
    for modelos, saida, titulo in [
        (FASE_C14, "01_comparacao_modelos.png", "Fase 1 (cardápio de 14 itens) — 100 mensagens de teste sintéticas"),
        (FASE_C17, "08_comparacao_modelos_v3.png", "Fase 2 (cardápio de 17 itens) — 100 mensagens de teste sintéticas"),
    ]:
        dados = carregar(modelos)
        if not dados:
            continue
        rotulos = [d[0] for d in dados]
        cores = [d[1] for d in dados]
        fig, eixos = plt.subplots(1, 3, figsize=(14, 4.6))
        barras(eixos[0], rotulos, [d[2]["acerto_exato"] * 100 for d in dados], cores,
               "Acerto exato do pedido (%)", lambda v: f"{v:.0f}%", 115)
        barras(eixos[1], rotulos, [d[2]["json_valido"] * 100 for d in dados], cores,
               "JSON válido (%)", lambda v: f"{v:.0f}%", 115)
        barras(eixos[2], rotulos, [d[2]["latencia_media_s"] for d in dados], cores,
               "Latência média (s)", lambda v: f"{v:.1f}s")
        for ax in eixos:
            ax.tick_params(axis="x", labelsize=8)
        fig.suptitle(titulo, fontsize=13, fontweight="bold", x=0.01, ha="left")
        fig.text(0.01, 0.01, "Fonte: outputs/resultados/*.json  •  GPU local RTX 5060 Ti  •  teste do mesmo gerador "
                 "do treino: não mede mensagens reais (ver provas finais)", fontsize=8, color="#666")
        fig.tight_layout(rect=(0, 0.04, 1, 0.93))
        fig.savefig(SAIDA / saida, dpi=150)
        plt.close(fig)
    print("imagens salvas em", SAIDA.relative_to(RAIZ))


if __name__ == "__main__":
    main()
