# Extrator de pedidos de WhatsApp com LLM ajustado (LoRA)

> **Status: em andamento.** Este README é provisório; os resultados finais e o modelo no Hugging Face ainda não foram publicados.
> A história completa, com erros e correções, está em [docs/DIARIO.md](docs/DIARIO.md). Estado atual (v5) e próximos passos: [docs/PROXIMOS_PASSOS.md](docs/PROXIMOS_PASSOS.md).

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
| `src/avaliar*.py`, `baseline_*.py` | Métricas e comparação com o modelo sem treino e com o Claude (API) |
| `docs/` | Diário do projeto e imagens de evidência |
| `outputs/resultados/` | Números e respostas de cada avaliação |

## Lições até agora
- Dados sintéticos davam 99% no teste do mesmo gerador, mas **30% em mensagens novas** (v2): o modelo aprendeu o estilo do gerador, não o problema. Ver o diário.
- O **v3** (cardápio de 17 itens, mensagens sem pedido e itens fora do cardápio no treino) fez **15/20 (75%)** numa prova com 20 mensagens novas, empatado com o Claude Haiku com regras (15/20). Com 20 mensagens é um empate técnico.
- O v3 tem um defeito conhecido: **perde bebidas no fim do pedido quando a mensagem tem pontuação** (24/40 de concordância com o Claude nas mensagens como foram escritas, 34/40 com a pontuação removida). A primeira tentativa de corrigir isso (v4: separadores com pontuação variada) **foi reprovada** no critério definido antes do resultado e ficou pior que o v3. Ablações mostraram que o culpado era a pontuação, e o **v5** (cada mensagem de treino ganha uma cópia com a pontuação mexida e o mesmo gabarito) **passou**: 35 a 37 de 40 mensagens iguais às do Claude nas 4 formas de escrita, contra 24 a 36 do v3 (diário, seções 13 a 16). A prova final com mensagens novas ainda está pendente.
- O gabarito da prova final foi escrito **antes** de rodar os modelos.
- Cardápio fixo: o modelo "sabe" o cardápio porque aprendeu no treino; se o cardápio mudar, precisa retreinar.

## Como rodar
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
python src/gerar_dados.py --n 2850 --seed 42
python src/treinar.py --epocas 3
python -m pytest tests
```
Para os baselines com o Claude, crie um arquivo `.env` com `ANTHROPIC_API_KEY=...` (o arquivo é ignorado pelo git).
