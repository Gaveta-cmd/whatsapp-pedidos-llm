# Roteiro do vídeo de 1 minuto (grave a tela; eu não consigo gravar vídeo)

1. **0:00 a 0:10, o problema.** Mostre uma mensagem de WhatsApp de pedido. Fale: "Cliente escreve solto, alguém precisa transformar em pedido."
2. **0:10 a 0:30, a demonstração.** Suba a API (`uvicorn --app-dir src api:app --port 8000`) e rode a chamada de exemplo do README (`curl ...`). Mostre o JSON saindo, depois uma mensagem que não é pedido voltando com `itens: []`.
3. **0:30 a 0:50, o resultado.** Abra `docs/evidencias/10_prova_final_v5.png`. Fale: "18 mensagens novas, gabarito feito antes: 17 de 18, empate técnico com o Claude."
4. **0:50 a 1:00, a honestidade.** Abra `docs/evidencias/09_robustez_pontuacao.png`: "Minha primeira correção foi reprovada; o diário tem tudo, inclusive os erros."

Dica: antes de gravar, a primeira chamada leva ~19 s (carrega o modelo). Faça uma chamada de aquecimento fora da gravação.
