# Próximos passos (estado em 31/10/2026)

## Onde paramos
- **v3**: 97% no teste sintético, 15/20 na prova final de 20 mensagens, mas perdia itens quando havia ponto final ou interrogação depois do pedido (24/40 nas mensagens como escritas).
- **v4** (pontuação variada nos separadores): **reprovado**, pior que o v3 (16/40). Retreinado do zero e ablacionado; ver diário, seções 13 a 15.
- **v5** (v3 + "gêmeos de pontuação" nos dados): **aprovado no critério** definido antes: 35, 35, 36 e 37 de 40 nas 4 formas de escrita (v3: 24, 27, 34, 36). Teste sintético 98%. Diário, seção 16.
- O adapter do v5 existe só no computador: `outputs/lora-qwen1.5b` e `outputs/lora-qwen1.5b-v5` (iguais). Os dados do v5 estão em `data/train.jsonl` e `data/val.jsonl`.

## Prova final limpa do v5 (a única coisa que depende de você)
1. Escreva 15 a 20 mensagens **novas**, bem pontuadas e com maiúsculas, como clientes de verdade, em `data/mensagens_finais_v5.txt` (uma por linha; crie o arquivo à mão, sem me mostrar antes).
2. Me chame: eu escrevo o gabarito (`data/final_gold_v5.jsonl`) **antes** de rodar qualquer modelo.
3. Rodar (usa a API do Claude para as comparações, custo de centavos):
```powershell
.\.venv\Scripts\python.exe src\avaliar_final.py --mensagens data\mensagens_finais_v5.txt --gold data\final_gold_v5.jsonl --nome final_v5 --rotulo lora_v5 --adapter outputs\lora-qwen1.5b-v5
```
4. Não alterar dados nem treino depois de ver o resultado.

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
