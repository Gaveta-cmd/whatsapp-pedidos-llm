# Próximos passos (estado em 31/10/2026)

## Onde paramos
- **v3**: 97% no teste sintético, 15/20 na prova final de 20 mensagens, mas perdia itens quando havia ponto final ou interrogação depois do pedido (24/40 nas mensagens como escritas).
- **v4** (pontuação variada nos separadores): **reprovado**, pior que o v3 (16/40). Retreinado do zero e ablacionado; ver diário, seções 13 a 15.
- **v5** (v3 + "gêmeos de pontuação" nos dados): **aprovado no critério** definido antes: 35, 35, 36 e 37 de 40 nas 4 formas de escrita (v3: 24, 27, 34, 36). Teste sintético 98%. Diário, seção 16.
- O adapter do v5 existe só no computador: `outputs/lora-qwen1.5b` e `outputs/lora-qwen1.5b-v5` (iguais). Os dados do v5 estão em `data/train.jsonl` e `data/val.jsonl`.

## Prova final limpa do v5: feita (31/10)
18 mensagens novas escritas por você; gabarito commitado antes de rodar (8c32da7). Resultado: **v5 17/18, Claude com regras 16/18, Claude sem regras 15/18, v3 16/18**: empate técnico. O erro do v5 (e dois do v3) é o mesmo item: **Coca 2L perdida no fim do pedido**. Diário, seção 17; imagem `10_prova_final_v5.png`.

## A "Coca 2L" não era o problema (diário, seção 18)
Teste controlado (`src/diagnosticar_item_final.py`, 6 frases-molde × 9 últimos itens): o v5 manteve o último item em **44/54** e o v3 em **24/54**; a Coca 2L foi mantida 12/12 no v5. O que concentra os erros do v5 é a frase que vem **depois** da lista, principalmente "Obrigado!" (3/9) e "Pagamento no cartão de débito, por favor." (6/9).

## Decisão aberta: fazer um v6?
- Passo barato antes: mesmos moldes, variando só o fechamento ("obrigado" minúsculo, sem "!", etc.) para saber o que pesa.
- Se valer a pena, o v6 mexe no gerador (fechamentos com maiúscula e "!" colados na lista) e precisa de uma **prova nova com mensagens que você ainda não escreveu** (a atual já foi vista).
- Alternativa: aceitar o v5 como está (empate técnico com o Claude na prova final), documentar o defeito e seguir para a API.

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
