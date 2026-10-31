# Estado final e pendências opcionais (31/10/2026)

## Onde terminou
- **Modelo final: v5** (LoRA no Qwen2.5-1.5B-Instruct, dados com "gêmeos de pontuação"). Adapter só no computador (`outputs/lora-qwen1.5b`).
- **Prova final (18 mensagens novas, gabarito commitado antes):** v5 17/18, Claude Haiku + regras 16/18, sem regras 15/18, v3 16/18. Empate técnico. Diário, seção 17.
- **Defeito conhecido:** pode perder o último item quando há frase de fechamento depois da lista ("Obrigado!"). Não é a Coca 2L (hipótese refutada). Diário, seção 18. Decisão: **não fazer v6**; documentado e encerrado.
- **API pronta:** `src/api.py` (`POST /extrair-pedido`), testada com o modelo real e com testes automáticos (29 testes).

## Pendências opcionais (não bloqueiam nada)
1. Publicar o adapter no Hugging Face com model card (precisa de um token seu). Hoje os pesos existem só no seu PC: faça um backup da pasta `outputs/lora-qwen1.5b`.
2. Integração com o n8n (chamar a API a partir de um fluxo).
3. Vídeo curto de demonstração e diagrama no README.
4. Artigo no LinkedIn (publicar só quando você decidir que acabou). Imagens seguras para postar em `docs/evidencias/`.
5. Tornar o repositório público (hoje privado); considerar tirar o `.venv` da pasta sincronizada do OneDrive.

## Reproduzir
```powershell
powershell -ExecutionPolicy Bypass -File .\experimentos.ps1 E_gemeos   # retreina o v5 (~25 min, GPU livre)
```
