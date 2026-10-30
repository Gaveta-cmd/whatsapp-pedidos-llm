# Próximos passos (estado em 30/10/2026)

## Onde paramos
- **v3** treinado e avaliado: 97% no teste sintético, 15/20 na prova final (empate técnico com o Claude), mas com um defeito: perde bebidas no fim do pedido quando a mensagem tem pontuação.
- **v4** (corrige pontuação/maiúsculas): dados prontos (3.000 exemplos), treino **interrompido** na época ~1 de 3. Há um checkpoint em `outputs/checkpoints/checkpoint-200`; ele **não vai para o GitHub** (fica só no computador).
- Critério de aceitação do v4, definido antes do resultado, em `src/robustez.py`: concordância com o Claude >= 34/40 nas 4 formas da mensagem e diferença <= 3 entre a melhor e a pior.

## Para rodar o v4 (no computador do projeto)
1. Feche jogos e programas que usam a placa (Wallpaper Engine, etc.).
2. No PowerShell, dentro da pasta do projeto:
```powershell
powershell -ExecutionPolicy Bypass -File .\rodar_v4.ps1
```
O script retoma do checkpoint, treina, roda o teste de robustez e o teste sintético, e atualiza os gráficos.
3. Veja `outputs/resultados/robustez_v4.json`. Se `"aprovado": true`, siga para a prova final.

## Prova final do v4 (só se passar no critério)
- Escrever um lote novo de 15 a 20 mensagens, **bem pontuadas e com maiúsculas**, em `data/mensagens_finais_v4.txt` (criar o arquivo à mão, sem pedir ao assistente).
- Escrever o gabarito (`data/final_gold_v4.jsonl`) **antes** de rodar os modelos.
- Rodar: `python src/avaliar_final.py --mensagens data/mensagens_finais_v4.txt --gold data/final_gold_v4.jsonl --nome final_v4 --rotulo lora_v4`
- Não alterar dados nem treino depois de ver o resultado.

## O que falta para fechar o portfólio
1. API FastAPI (`POST /extrair-pedido`) e integração com o n8n.
2. Publicar o adapter no Hugging Face com model card (os adapters v1 a v3 só existem localmente).
3. Otimizar a inferência (hoje 3,4 s/mensagem contra 1,6 s do Claude).
4. README final com tabela de resultados, diagrama e vídeo curto.
5. Artigo no LinkedIn (rascunho já existe no histórico da conversa; só publicar depois de tudo pronto).
