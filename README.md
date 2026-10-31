# Extrator de pedidos de WhatsApp com LLM ajustado (LoRA)

> **Status: versão final = v5, com API.** Os pesos do adapter não estão publicados (ficam só na máquina de quem treinou); para reproduzir, veja "Como rodar".
> A história completa, com erros e correções, está em [docs/DIARIO.md](docs/DIARIO.md). Pendências opcionais: [docs/PROXIMOS_PASSOS.md](docs/PROXIMOS_PASSOS.md).

**Resumo dos resultados** (acerto exato; endereço comparado literalmente)

| Teste | LoRA v5 | Claude Haiku + regras | Claude Haiku sem regras |
|---|---|---|---|
| 18 mensagens novas escritas à mão (prova final, gabarito commitado antes) | **17/18** | 16/18 | 15/18 |
| 100 mensagens sintéticas (mesmo gerador do treino; o Claude não treinou nelas) | 98% | 90% | 80% |
| Concordância com o Claude, 40 mensagens × 4 formas de escrita | 35 a 37 de 40 | — | — |

É um **empate técnico** com o Claude nas mensagens à mão (1 a 2 mensagens de diferença em 18). Limitação conhecida: o modelo ainda pode perder o **último item** do pedido quando há uma frase de fechamento depois da lista (ex.: "Obrigado!"); isso aparece em cerca de 1 a cada 5 frases de um teste controlado (diário, seções 17 e 18).

Transforma uma mensagem livre de cliente em um pedido estruturado (JSON) para um espetinho:

```
"boa noite, quero 2 espetinho de carne, 1 de frango sem farofa e uma coca lata"
→ {"itens":[{"produto":"espetinho de carne","qtd":2,"obs":null},
            {"produto":"espetinho de frango","qtd":1,"obs":"sem farofa"},
            {"produto":"coca-cola lata","qtd":1,"obs":null}],"endereco":null,"pagamento":null}
```

Uma lista de itens vazia significa que a mensagem **não é um pedido** (pergunta, saudação, reclamação).

> **Sobre o uso de IA:** este projeto foi desenvolvido com apoio de um assistente de IA (Claude Code). Os dados, as regras de negócio, o gabarito das provas e a análise dos resultados foram definidos e revisados por mim.

## O que tem aqui
| Pasta/arquivo | Para quê |
|---|---|
| `src/schema.py` | Schema Pydantic do pedido (a "régua" de validação) |
| `src/gerar_dados.py` | Gerador de dados sintéticos a partir do cardápio (`data/cardapio.json`) |
| `src/treinar.py` | Fine-tuning com LoRA (Qwen2.5-1.5B-Instruct) |
| `src/api.py` | API FastAPI: `POST /extrair-pedido` com `{"mensagem": "..."}` devolve o pedido em JSON |
| `src/avaliar*.py`, `baseline_*.py` | Métricas e comparação com o modelo sem treino e com o Claude (API) |
| `docs/` | Diário do projeto e imagens de evidência |
| `outputs/resultados/` | Números e respostas de cada avaliação |

## Lições até agora
- Dados sintéticos davam 99% no teste do mesmo gerador, mas **30% em mensagens novas** (v2): o modelo aprendeu o estilo do gerador, não o problema. Ver o diário.
- O **v3** (cardápio de 17 itens, mensagens sem pedido e itens fora do cardápio no treino) fez **15/20 (75%)** numa prova com 20 mensagens novas, empatado com o Claude Haiku com regras (15/20). Com 20 mensagens é um empate técnico.
- O v3 tem um defeito conhecido: **perde bebidas no fim do pedido quando a mensagem tem pontuação** (24/40 de concordância com o Claude nas mensagens como foram escritas, 34/40 com a pontuação removida). A primeira tentativa de corrigir isso (v4: separadores com pontuação variada) **foi reprovada** no critério definido antes do resultado e ficou pior que o v3. Ablações mostraram que o culpado era a pontuação, e o **v5** (cada mensagem de treino ganha uma cópia com a pontuação mexida e o mesmo gabarito) **passou**: 35 a 37 de 40 mensagens iguais às do Claude nas 4 formas de escrita, contra 24 a 36 do v3 (diário, seções 13 a 16).
- **Prova final do v5** (18 mensagens novas, escritas por mim, gabarito commitado antes de rodar): v5 **17/18**, Claude Haiku com regras 16/18, sem regras 15/18, v3 16/18. É um **empate técnico** (diferença de 1 a 2 mensagens em 18). O único erro do v5 é o defeito conhecido: perdeu o último item (Coca 2L) antes do fim de frase; ele ficou mais raro, mas não sumiu. Detalhes e ressalvas no diário, seção 17.
- O gabarito das provas finais foi escrito **antes** de rodar os modelos.
- Cardápio fixo: o modelo "sabe" o cardápio porque aprendeu no treino; se o cardápio mudar, precisa retreinar.

## Como rodar
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
python src/gerar_dados.py --n 4000 --seed 42 --manter-teste --caixa v4 --pontuacao v3 --gemeos   # dados do v5
python src/treinar.py --epocas 3                                                               # ~25 min numa RTX 5060 Ti
python -m pytest tests
uvicorn --app-dir src api:app --port 8000                                                      # sobe a API
```
Exemplo de chamada (com o servidor no ar):
```bash
curl -X POST http://127.0.0.1:8000/extrair-pedido -H "Content-Type: application/json" \
  -d '{"mensagem": "quero 2 espetinho de carne e uma coca lata, pago no pix"}'
```
Na máquina de desenvolvimento a primeira chamada leva ~19 s (carrega o modelo) e as seguintes ~1 s (medida informal, uma amostra).
Para os baselines com o Claude, crie um arquivo `.env` com `ANTHROPIC_API_KEY=...` (o arquivo é ignorado pelo git).
