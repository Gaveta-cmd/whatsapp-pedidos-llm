# Rascunho do artigo (NÃO publicado): ajuste ao seu jeito antes de postar

**Título sugerido:** Treinei um modelo pequeno para ler pedidos de WhatsApp. Ele empatou com o Claude, e os erros me ensinaram mais que os acertos.

**O problema.** Um espetinho recebe pedidos soltos no WhatsApp: "boa noite, quero 2 de carne, 1 de frango sem farofa e uma coca lata, pago no pix". Alguém precisa transformar isso em pedido estruturado. Eu quis ver se um modelo pequeno (Qwen2.5-1.5B), ajustado com LoRA na minha própria placa de vídeo, conseguia fazer isso.

**O que construí.** Gerador de dados sintéticos a partir do cardápio, treino com LoRA, um schema Pydantic para validar a saída, uma API FastAPI e uma avaliação comparando com o Claude Haiku (com e sem regras de negócio). O código e o diário completo, com os erros, estão no repositório.

**O resultado, sem exagero.** Numa prova final com 18 mensagens novas, escritas por mim, com o gabarito commitado antes de rodar qualquer modelo: modelo ajustado 17/18, Claude com regras 16/18, Claude sem regras 15/18. Com 18 mensagens isso é um empate técnico, não uma vitória.

**O que eu mais aprendi (os erros):**
1. **Teste sintético engana.** O modelo tirava 99% no teste do mesmo gerador do treino e cerca de 30% em mensagens escritas à mão. Ele tinha aprendido o estilo do gerador, não o problema.
2. **Minha primeira correção piorou tudo.** Variei a pontuação dos dados de treino e o modelo ficou pior que o anterior. Eu tinha definido o critério de aprovação antes de ver o resultado, então não deu para "interpretar" a favor. Reprovei meu próprio modelo.
3. **Mudar um fator por vez resolveu.** Com ablações (tirar caixa alta, tirar pontuação, uma de cada vez) descobri que o problema era o fim de frase depois da lista de itens: o modelo perdia o último item. A correção foi dar a cada mensagem de treino cópias com a pontuação mexida e o mesmo gabarito.
4. **Hipótese minha caiu.** Achei que o erro restante era específico da "Coca 2L". Um teste controlado mostrou que não era. Documentei a hipótese refutada em vez de esconder.

**Limitações.** Cardápio fixo (mudou o cardápio, retreina), mensagens escritas por uma pessoa só, e o modelo ainda pode perder o último item quando há um "Obrigado!" depois da lista.

**Sobre o uso de IA.** Desenvolvi o projeto com apoio de um assistente de IA (Claude Code). Os dados, as regras de negócio, o gabarito da prova e a análise dos resultados foram definidos e revisados por mim.

**Link:** repositório (tornar público antes de postar) e `docs/evidencias/` (gráficos prontos, sem chaves nem dados pessoais).

**Gancho para entrevista:** "Eu defino o critério de sucesso antes de rodar o experimento, e publico os resultados ruins junto com os bons."
