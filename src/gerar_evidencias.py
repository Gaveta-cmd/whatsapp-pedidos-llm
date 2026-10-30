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
MODELOS = [
    ("baseline_base", "Qwen 1.5B\nsem treino", "#9aa0a6"),
    ("lora_qwen_v1", "Qwen + LoRA\nv1", "#7aa7e8"),
    ("lora_qwen_v2", "Qwen + LoRA\nv2", "#2f6fdb"),
    ("baseline_claude", "Claude Haiku\n(API)", "#e08a3c"),
    ("baseline_claude_regras", "Claude Haiku\n+ regras", "#c2611b"),
]


def carregar() -> list[tuple[str, str, dict]]:
    achados = []
    for arq, rotulo, cor in MODELOS:
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


def grafico_final() -> None:
    """Prova final (20 mensagens novas): total, com pedido e sem pedido."""
    caminho = RES / "final_prova.json"
    if not caminho.exists():
        return
    r = json.loads(caminho.read_text(encoding="utf-8"))["resumo"]
    sistemas = [("lora_v2", "Qwen + LoRA v2", "#2f6fdb"), ("claude_sem_regras", "Claude\nsem regras", "#e08a3c"),
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
    fig.suptitle("Prova final: 20 mensagens novas, nunca vistas no treino nem no desenvolvimento",
                 fontsize=13, fontweight="bold", x=0.01, ha="left")
    fig.text(0.01, 0.01, "Gabarito escrito antes de rodar os modelos  •  endereço comparado literalmente (critério estrito)",
             fontsize=8, color="#666")
    fig.tight_layout(rect=(0, 0.04, 1, 0.93))
    fig.savefig(SAIDA / "05_prova_final.png", dpi=150)
    plt.close(fig)


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    grafico_final()
    dados = carregar()
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
    fig.suptitle("Extração de pedidos de WhatsApp — 100 mensagens de teste (sintéticas)",
                 fontsize=13, fontweight="bold", x=0.01, ha="left")
    fig.text(0.01, 0.01, "Fonte: outputs/resultados/*.json  •  GPU local RTX 5060 Ti  •  teste sintético, "
             "ver DIARIO.md para o teste com mensagens reais", fontsize=8, color="#666")
    fig.tight_layout(rect=(0, 0.04, 1, 0.93))
    fig.savefig(SAIDA / "01_comparacao_modelos.png", dpi=150)
    plt.close(fig)

    # Custo: só o Claude tem custo por mensagem (modelo local roda na própria GPU)
    claude = next((d for d in dados if d[0].startswith("Claude")), None)
    if claude and "custo_por_1000_msgs_usd" in claude[2]:
        print("Claude: US$ %.3f por 1.000 mensagens" % claude[2]["custo_por_1000_msgs_usd"])
    print("imagens salvas em", SAIDA.relative_to(RAIZ))


if __name__ == "__main__":
    main()
