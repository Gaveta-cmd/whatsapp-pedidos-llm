# Próximos passos (estado em 31/10/2026)

## Onde paramos
- **v3**: 97% no teste sintético, 15/20 na prova final de 20 mensagens, mas perdia itens quando havia ponto final ou interrogação depois do pedido (24/40 nas mensagens como escritas).
- **v4** (pontuação variada nos separadores): **reprovado**, pior que o v3 (16/40). Retreinado do zero e ablacionado; ver diário, seções 13 a 15.
- **v5** (v3 + "gêmeos de pontuação" nos dados): **aprovado no critério** definido antes: 35, 35, 36 e 37 de 40 nas 4 formas de escrita (v3: 24, 27, 34, 36). Teste sintético 98%. Diário, seção 16.
- O adapter do v5 existe só no computador: `outputs/lora-qwen1.5b` e `outputs/lora-qwen1.5b-v5` (iguais). Os dados do v5 estão em `data/train.jsonl` e `data/val.jsonl`.

## Prova final limpa do v5: feita (31/10)
18 mensagens novas escritas por você; gabarito commitado antes de rodar (8c32da7). Resultado: **v5 17/18, Claude com regras 16/18, Claude sem regras 15/18, v3 16/18**: empate técnico. O erro do v5 (e dois do v3) é o mesmo item: **Coca 2L perdida no fim do pedido**. Diário, seção 17; imagem `10_prova_final_v5.png`.

## Decisão aberta: investigar a "Coca 2L"?
Hipótese ainda não testada: o defeito que sobrou pode ser específico de "Coca 2L" (ambígua com "coca" = lata), e não só da pontuação. Para testar sem mexer na prova final: um diagnóstico que troca só o último item das mesmas mensagens (Coca 2L por suco, água etc.) e vê se o modelo ainda perde. Se confirmar, uma correção nos dados seria um **v6** e precisaria de uma **prova nova com mensagens que você ainda não escreveu** (a atual já foi vista).

## Reproduzir os experimentos
```powershell
powershell -ExecutionPolicy Bypass -File .\experimentos.ps1 E_gemeos
```
Variantes disponíveis em `experimentos.ps1` (A a E). Cada uma leva ~25 min na RTX 5060 Ti com a placa livre.

## O que falta para fechar o portfólio
1. API FastAPI (`POST /extrair-pedido`) e integração com o n8n.
2. Publicar o adapter no Hugging Face com model card (os adapters só existem localmente; precisa de token seu).
3. Otimizar a inferência (hoje 3,4 s/mensagem contra 1,6 s do Claude).
4. README final com tabela de resultados, diagrama e vídeo curto.
5. Artigo no LinkedIn (rascunho já existe no histórico da conversa; só publicar depois de tudo pronto).
