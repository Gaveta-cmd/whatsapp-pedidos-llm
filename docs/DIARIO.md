# Diário do projeto: LLM que extrai pedidos de WhatsApp

Atualizado em 30/10/2026. Material de apoio para o README e para o post. Todos os números vêm de
`outputs/resultados/*.json`; as imagens são geradas por `python src/gerar_evidencias.py`.

## Evidências (docs/evidencias/)
- `01_comparacao_modelos.png`: gráfico de acerto, JSON válido e latência (`src/gerar_evidencias.py`)
- `02_terminal_testes.png`: 19 testes automáticos passando
- `03_erros_modelo_v1.png`: onde o modelo v1 errou nas mensagens escritas à mão (JSON inválido, "1 de cada", "capricha")
- `04_terminal_resultados.png`: tabela de resultados
- `05_prova_final_v2.png`: prova final do v2 (cardápio de 14 itens), 20 mensagens novas
- `06_erros_prova_final.png`: principais erros do v2 na prova final
- `07_prova_final_v3.png`: prova final do v3 (cardápio de 17 itens), 20 mensagens novas
- `08_comparacao_modelos_v3.png`: teste sintético da fase 2 (cardápio de 17 itens)
Os "prints de terminal" são gerados por `src/gerar_prints.py` a partir da saída real e passam por um filtro que remove chaves, e-mails e caminhos do computador.

## O problema
Cliente de delivery manda texto livre: *"boa noite, quero 2 espetinho de carne, 1 de frango sem farofa e uma coca lata"*.
Alguém precisa ler e digitar. Objetivo: transformar a mensagem em um pedido estruturado (JSON).

## Resultados até aqui (100 mensagens de teste sintéticas)

| Modelo | JSON válido | Acerto exato | Latência média | Custo / 1.000 msgs |
|---|---|---|---|---|
| Qwen2.5-1.5B sem treino | 99% | 28% | 5,3 s | ~zero (GPU local) |
| Qwen2.5-1.5B + LoRA v1 | 100% | 100% | 3,4 s | ~zero (GPU local) |
| Claude Haiku 5.5 (API) | 100% | 99% | 1,5 s | US$ 0,13 |

Imagem: `docs/evidencias/01_comparacao_modelos.png`

**Atenção:** o 100% do v1 é em dados do mesmo gerador usado no treino. Não prova nada sobre clientes reais.

## Linha do tempo: o que deu errado e o que mudou

### 1. Erros nos meus próprios dados (antes de treinar)
Ao olhar os "erros" do Claude no teste, descobri que 3 de 4 eram culpa do gerador de dados:
- o gerador colocava erro de digitação **dentro do endereço** ("av brasli") mas o gabarito tinha o endereço certo;
- o produto "porção de mandioca" era chamado pelo cliente de "mandioca **frita**", e o Claude entendia "frita" como observação;
- "Av." contra "av" contava como erro por pura formatação.

Correções: endereço copiado literalmente; produto renomeado para "porção de mandioca frita"; normalização de pontuação.
No primeiro teste o Claude marcou 96%; depois de corrigir o gerador e regerar o teste, 99% (são conjuntos de teste diferentes, então a comparação é só indicativa). Lição: olhar os erros antes de treinar, senão se ensina o erro.

### 2. Respostas cortadas do Claude
1 de 100 respostas parava no meio por limite de tokens (`max_tokens=400`). Aumentei para 2000 e o JSON válido foi de 99% para 100%.

### 3. O que o modelo sem treino erra
- inventa produtos fora do cardápio (ex.: "queijo coalho" em vez de "espetinho de queijo coalho");
- inventa forma de pagamento ("pix") quando o cliente não disse;
- troca quantidades.

### 4. Teste com mensagens escritas à mão (40 mensagens, imitando clientes reais)
Modelo v1 e Claude concordaram em **36 de 40** (90%), bem abaixo dos 100% do teste sintético. Os 4 desencontros:
- "manda a **chave pix**": o v1 escreveu `"pagamento":"chave pix"` e o JSON ficou inválido (2 casos);
- "1 de **cada** espetinho": o v1 listou só 1 dos 5 espetinhos;
- "**capricha** na farofa": o v1 criou 5 porções de farofa.

Causa: nos dados de treino ninguém nunca escreveu essas frases. O modelo decorou o estilo do gerador.
A validação do schema (Pydantic) barrou o pagamento inválido em vez de deixar passar um pedido estragado.

### 5. Retreino v2
- Gerador ampliado com frases de clientes reais (chave pix, troco, maquininha, "de cada", perguntas soltas).
- Regra de negócio decidida: "capricha na farofa" = 1 farofa com observação `caprichar`.
- 1.500 exemplos de treino (antes 800). Teste sintético mantido idêntico para comparar v1 e v2.
- As 40 mensagens reais passam a ser "de desenvolvimento" (foram usadas para melhorar o gerador). A prova final será com 20 mensagens novas, nunca vistas.

### 6. Resultado do v2
Treino: 1.500 exemplos, 3 épocas, ~8,5 min (o v1 levou ~24 min; lote menor na GPU).

| Modelo | JSON válido | Acerto exato (teste sintético) | Concordância com Claude (40 msgs à mão) |
|---|---|---|---|
| v1 | 100% | 100% | 36/40 |
| v2 | 100% | 99% | 38/40 |

Resolvidos no v2: "chave pix" (JSON inválido) e "1 de cada espetinho".
Ainda errados, 2 casos:
- "Manda a chave pix de vcs": o v2 preencheu pagamento = pix; o Claude deixou vazio. Quem tem razão é uma decisão de negócio (pedir a chave do pix indica que vai pagar no pix?).
- "Capricha na farofa pfv": o v2 **omitiu** a farofa; a regra é 1 farofa com obs "caprichar". Erro real do modelo.

Ressalvas honestas:
- Essas 40 mensagens foram usadas para melhorar o gerador do v2, então a melhora era esperada. Elas não provam generalização; só a prova final com mensagens novas prova.
- O Claude nessa comparação não conhece a regra "caprichar" (o prompt dele não a menciona), então o desencontro no #23 não é uma falha dele.
- O acerto de 99% no sintético (antes 100%) vem de 1 mensagem; com 100 exemplos essa diferença é ruído.

### 7. Comparação justa: Claude com as mesmas regras
Decisão de negócio: pedir a chave do pix = pagamento pix. Para o Claude não ser prejudicado por não conhecer as regras (pix, "caprichar", "de cada", troco), criei uma versão do prompt dele com essas regras.
Resultado no teste sintético: 97% de acerto exato (sem regras: 99%), JSON 100%, 1,5 s, US$ 0,16 / 1.000 msgs. A diferença de 2 mensagens é ruído, e o teste sintético antigo quase não contém as frases das regras novas, então ele não mede se as regras ajudam. Isso será medido na prova final com mensagens novas.

### 8. Prova final: 20 mensagens novas (resultado ruim, e honesto)
Gabarito escrito **antes** de rodar os modelos. Critério estrito (endereço comparado literalmente). 17 mensagens com pedido, 3 sem pedido.

| | Acerto exato | Com pedido (17) | Sem pedido (3) |
|---|---|---|---|
| Qwen + LoRA v2 | 6/20 (30%) | 6/17 | 0/3 |
| Claude sem regras | 17/20 (85%) | 14/17 | 3/3 |
| Claude com regras | 18/20 (90%) | 15/17 | 3/3 |

O 99% do teste sintético não generalizou: era o modelo acertando o estilo do meu gerador. O que ele errou são justamente situações que o gerador nunca produziu:
- **Itens fora do cardápio** (batata frita, cerveja, pastel, picanha, arroz): o modelo os escreve como se fossem produtos, em vez de ignorar. Nos dados de treino todo item mencionado estava no cardápio.
- **Mensagens sem pedido** ("até que horas abrem?", "aceitam vale refeição?"): 0/3. O modelo inventa um pedido (5 espetinhos). Todo exemplo de treino tinha ao menos 1 item.
- **"2 de cada acompanhamento"**: só treinou "de cada espetinho"; inventou "porção de frango", "porção de linguiça".
- **Quantidade depois do produto** ("coração 3"): trocou 3 por 2.
- **Uma mensagem com JSON inválido**, numa frase condicional ("se não tiver cupim, manda...").
- Alguns itens inventados mesmo dentro do cardápio (acrescentou 5 espetinhos de linguiça num pedido de pão de alho).

Erros de endereço (análise a posteriori, não muda o critério oficial): o modelo e o Claude reescrevem o endereço ("quadra 10, conjunto 3, casa 8"; "Rua das Palmeiras, 45" para "rua das palmeiras num 45"). Ignorando vírgulas, o modelo ganharia 2 acertos; não é a causa principal.

Erros do Claude: #4 (aplicou "caprichar" a todos os espetinhos; o gabarito, discutível, não aplica) e #8 (endereço reformatado).

Honestidade sobre o protocolo: o conteúdo dessas 20 mensagens foi exibido ao Claude automaticamente pelo editor antes da execução. Nenhum dado, treino ou schema foi alterado em função delas, e o gabarito foi escrito antes de rodar qualquer modelo.

Conclusão: o fine-tuning ensina o formato e o vocabulário do cardápio (99% no teste sintético contra 30% na prova final mostra o tamanho do buraco), mas os dados precisam cobrir os casos reais: mensagens sem pedido, produtos que não existem, e mais variedade de sintaxe. Sem isso, o Claude via API é muito mais confiável.

### 9. v3: cardápio de 17 itens e casos que faltavam
Decisão de negócio: o cardápio ganhou espetinho de picanha, porção de arroz e porção de feijão (17 itens). "1 de cada acompanhamento" = um de cada acompanhamento do cardápio. Por isso os resultados são separados em duas fases (cardápio de 14 itens: v1 e v2; cardápio de 17 itens: v3), cada uma com o seu teste sintético. Os resultados antigos ficam com sufixo `_c14`.

O gerador do v3 passou a incluir: mensagens sem pedido (resposta com itens vazio), menções a produtos fora do cardápio (ignorados), "de cada acompanhamento", quantidade depois do produto ("linguiça 2"), frases condicionais e endereços em formatos variados. 2.465 exemplos de treino.

Teste sintético novo (100 mensagens, mais difícil que o antigo):

| | JSON válido | Acerto exato | Latência | Custo / 1.000 msgs |
|---|---|---|---|---|
| Qwen sem treino | 92% | 15% | 4,8 s | ~zero |
| **Qwen + LoRA v3** | 99% | **97%** | 3,4 s | ~zero |
| Claude Haiku sem regras | 100% | 80% | 1,6 s | US$ 0,16 |
| Claude Haiku com regras | 100% | 90% | 1,6 s | US$ 0,19 |

Imagem: `08_comparacao_modelos_v3.png`. Lembrete: este teste vem do mesmo gerador do treino.

### 10. Um defeito do v3: a pontuação
Nas 40 mensagens escritas à mão, o v3 concordou com o Claude em apenas 24/40 (o v2: 37/40 contra as mesmas respostas). Em 16 mensagens o v3 deixou um item de fora, quase sempre uma bebida no fim do pedido.
Experimento (mesmas 40 mensagens, quatro formas):

| Forma da mensagem | v3 | v2 |
|---|---|---|
| Original | 24/40 | 37/40 |
| Tudo em minúsculas | 27/40 | 37/40 |
| Sem pontuação | 34/40 | 35/40 |
| Minúsculas e sem pontuação | 36/40 | 35/40 |

A causa principal é a pontuação, não as maiúsculas. Hipótese (não provada): os exemplos novos com perguntas ("?") e frases soltas ensinaram o v3 a tratar o que vem depois de um ponto como conversa à parte, descartando o item logo antes dele. Correção planejada para o v4: treinar com pontuação e maiúsculas muito variadas e usar esse mesmo experimento como teste de aceitação (concordância parecida nas quatro formas).

### 11. Prova final do v3: 20 mensagens novas
O v3 foi treinado antes de as mensagens existirem. O gabarito foi escrito antes de rodar os modelos, com alternativas aceitas nos casos ambíguos. Critério estrito: endereço comparado literalmente. 17 mensagens com pedido e 3 sem pedido.

| | Acerto exato | Com pedido (17) | Sem pedido (3) |
|---|---|---|---|
| Qwen + LoRA v3 | 15/20 (75%) | 13/17 | 2/3 |
| Claude sem regras | 14/20 (70%) | 12/17 | 2/3 |
| Claude com regras | 15/20 (75%) | 12/17 | 3/3 |

Imagem: `07_prova_final_v3.png`. A diferença entre o v3 e o Claude é de uma mensagem em 20, então é um empate técnico, não uma vitória.

Erros do v3 (5): (1) numa reclamação sem pedido ("meu pedido da rua 12 já saiu?"), copiou "rua 12" como endereço; (2) "capricha no ponto da carne, bem mal passada": escreveu `caprichar` em vez de `mal passado`; (3) "1 de cada acompanhamento": devolveu 4 dos 6 acompanhamentos, faltaram arroz e feijão (itens mais novos); (4) deixou de fora "1 agua sem gas" no fim do pedido (o defeito de bebidas, mesmo sem pontuação); (5) "troco p 100": respondeu pagamento pix em vez de dinheiro.
Erros do Claude com regras (5): reformata endereços ("Condomínio Residencial Flores, apto 301" para "cond residencial flores apto 301"), o que o critério literal pune; esqueceu o pão de alho num "1 de cada" de 12 itens; e interpretou "capricha" de forma diferente do gabarito em 2 mensagens.

Ressalvas honestas:
- 20 mensagens é pouco: cada mensagem vale 5 pontos percentuais.
- Esse lote foi escrito em minúsculas e quase sem pontuação, o estilo em que o v3 vai melhor (ver seção 10). O lote anterior, mais pontuado, deu 24/40. O resultado depende do estilo de escrita, e é isso que o v4 deve corrigir.
- O conteúdo das mensagens foi lido por mim para escrever o gabarito, depois do treino do v3; nenhum dado ou treino foi alterado a partir delas.
- Latência: v3 local 3,4 s contra 1,6 s do Claude (inferência local ainda sem otimização).
- Custo: v3 roda na própria GPU, sem custo por mensagem; Claude com regras custa cerca de US$ 0,19 por 1.000 mensagens.

### 12. v4 (em andamento)
Mudanças nos dados: pontuação variada (ponto, reticências, exclamação, quebra de linha), metade das mensagens em caixa de frase, reclamações com rua sem endereço no gabarito, "troco p 100". 3.000 exemplos. O critério de aceitação foi fixado em `src/robustez.py` antes de qualquer resultado.
Ocorrências: o primeiro treino ficou lento (a placa estava dividida com outros programas, memória em 15,9 de 16 GB), foi suspenso, e o processo congelado acabou encerrado pelo app, perdendo o progresso (o script ainda não tinha checkpoint). O script agora salva a cada 50 passos e aceita `--retomar`. O segundo treino foi interrompido por escolha na época ~1 de 3, com checkpoint salvo. Ver `docs/PROXIMOS_PASSOS.md`.
Lição de engenharia: treinos longos precisam de checkpoint desde o primeiro disparo.

### 13. Resultado do v4: reprovado no critério
O treino foi retomado do checkpoint e terminou em ~8 min com a placa livre (a lentidão anterior era disputa pela GPU). Perda final de treino: 0,0019.

| Concordância com o Claude em 40 mensagens reais | v3 | v4 |
|---|---|---|
| como foram escritas | 24/40 | 21/40 |
| minúsculas | - | 22/40 |
| sem pontuação | 34/40 | 27/40 |
| minúsculas e sem pontuação | - | 26/40 |

Critério fixado antes do resultado: >= 34/40 em todas as formas e diferença <= 3. **Reprovado**: o v4 ficou abaixo do v3 em todas as comparações possíveis, e o teste sintético também caiu (92% contra 97% do v3). JSON válido continua em 100%, então o problema é de conteúdo, não de formato.

O que NÃO sabemos: por que piorou. Hipóteses ainda não testadas: (a) a mudança do gerador (pontuação, caixa de frase, mais ruído) deixou o treino mais difícil e 3 épocas em 3.000 exemplos não bastam; (b) as 40 mensagens reais já estão contaminadas pelo estilo que o v3 aprendeu a imitar (elas guiaram o v3); (c) variação normal entre treinos (um treino só, sem repetição). Nenhuma foi confirmada; não vamos afirmar causa sem experimento.
Decisão: o v3 continua sendo o melhor modelo medido. Não há prova final do v4, pois não passou no critério.

### 14. Diagnóstico do v4 (parcial)
Script `src/diagnosticar.py`: classifica cada divergência do modelo em relação ao Claude (nas 40 mensagens, 4 formas de escrita). Resultados em `outputs/resultados/diagnostico_v3.json` e `diagnostico_v4.json`.
- **Quase todo erro é "item faltando"**: v4 com 18 de 19 erros (mensagens como escritas), v3 com 13 de 16. Quantidade, endereço e pagamento quase não erram.
- **O item que some é o último da lista**: somando as 4 formas de escrita, no v4 46 dos 58 itens perdidos eram o último (no v3, 28 de 36). Os pedidos têm 3 ou 4 itens.
- **Itens mais perdidos no v4**: suco de laranja (19), queijo coalho (12), guaraná lata (8), farofa (6). Em todas as mensagens com erro há uma frase depois do pedido (pagamento ou pergunta).
- O erro não é de pontuação: sem pontuação o v4 continuou ruim (27/40), enquanto o v3 melhorou (34/40). A hipótese do v4 ("o problema é pontuação") estava, no mínimo, incompleta.

**Hipótese 1: a frase depois do pedido (pagamento/pergunta) faz o modelo encerrar a lista. Teste contrafactual nas 40 mensagens (só itens comparados com o Claude, 1 execução):**

| Versão da mensagem | v3 itens exatos / último item presente | v4 itens exatos / último item presente |
|---|---|---|
| como foi escrita | 26 / 28 | 21 / 25 |
| só a frase com os itens (sem pagamento/pergunta) | 25 / 26 | 25 / 28 |
| frase de pagamento/pergunta ANTES dos itens | 30 / 31 | 24 / 26 |

Resultado: **a hipótese quase não se sustenta.** Sem a frase de pagamento o v3 não melhorou (26→25) e o v4 melhorou 4 em 40 (21→25), mas o último item continuou faltando em 12 a 14 mensagens. As diferenças são de +-4 em 40 mensagens, com uma execução, e podem ser ruído. Limitação: o filtro que separa "frase de itens" do resto é uma regra simples (regex) que escrevi, e pode errar.

**Achado mais forte: o v4 perde o último item até no teste sintético**, que é do mesmo gerador do treino. Teste sintético (100 mensagens): v3 com 3 erros, nenhum de item faltando; v4 com 8 erros, 6 deles item faltando, e em 5 desses 6 o item perdido era o último (ex.: "...mais 2 pão de alho" no fim da mensagem). Ou seja, o defeito **não vem da diferença entre mensagens sintéticas e reais**: o v4 aprendeu a cortar o fim da lista.

**Hipótese 2: os dados de treino do v4 teriam menos pedidos longos ou mais exemplos em que o último item some do texto.** Comparei o treino do v3 (2.465 exemplos, recuperado do primeiro commit) com o do v4 (3.000): média de itens 3,00 contra 2,95, pedidos com 3+ itens 54% contra 53%, último item sem palavra-chave no texto 7,1% contra 7,3% (mesma taxa nos dois, medida por regras simples que erram com erro de digitação), mensagens que terminam no último item 6,3% contra 5,9%. Praticamente iguais, então **os dados não explicam a piora** (pelo menos nessas medidas).

**O que sobra, sem confirmação:** (a) o treino do v4 foi interrompido e retomado do checkpoint-200 (num segundo processo); o retomar pode ter deixado o treino diferente de uma execução contínua; (b) variação normal entre treinos (um treino só de cada versão); (c) algum efeito da pontuação/caixa de frase que as medidas acima não pegam. Experimento que separa (a)/(b) de (c): treinar de novo os dados do v4 **do zero, sem interrupção, mesma semente** (~12 min de treino). Se o resultado ficar parecido com o v3, a causa era o retomar; se continuar ruim, a causa está nos dados novos ou no acaso do treino.

### 15. Retreino, ablações e a pista da pontuação (noite de 30 para 31/10)
**Retreino do v4 do zero** (sem interrupção; corrigi também uma linha de `treinar.py` em que um comentário tinha engolido `remove_unused_columns=False, seed=42`): teste sintético 98% (melhor que o v3, 97%; o v4 retomado tinha 92%), mas nas 40 mensagens reais **16, 18, 29 e 29 de 40**: continua reprovado. Conclusão: o treino retomado não era a causa do defeito.

**Ablações** (`experimentos.ps1`, mudando uma coisa por vez nos dados do v4; uma execução de cada, então diferenças pequenas podem ser ruído):

| Dados de treino | original | minúsculas | sem pontuação | os dois | sintético |
|---|---|---|---|---|---|
| v3 (referência, treino antigo) | 24 | 27 | 34 | 36 | 97% |
| v4 do zero | 16 | 18 | 29 | 29 | 98% |
| B: v4 com a caixa do v3 | 19 | 20 | 31 | 30 | 99% |
| C: v4 com a pontuação/separadores do v3 | 26 | 27 | 33 | 33 | 96% |

Leitura: a caixa (maiúsculas) pouco explica; **a pontuação nova do v4 piorou o modelo** (com a do v3, ele volta ao nível do v3). A variante A (controle com os dados originais do v3) falhou por um erro de arquivo meu (BOM) e foi pulada; C já indica que o pipeline reproduz o v3.

**Qual sinal de pontuação faz o modelo perder itens** (`src/ablacao_pontuacao.py`, só itens comparados com o Claude, em 40 mensagens):

| Forma da mensagem | v3 | C | v4 do zero |
|---|---|---|---|
| original | 26 | 26 | 17 |
| sem vírgulas | 28 | 27 | 20 |
| sem ponto final/interrogação/exclamação | 35 | 31 | 29 |
| fim de frase vira vírgula | 30 | 28 | 22 |
| sem nenhuma pontuação | 34 | 33 | 29 |

Leitura: o que atrapalha é sobretudo o **fim de frase** (ponto, interrogação) depois da lista de itens; as vírgulas pesam pouco. Todos os modelos, inclusive o v3, sofrem com isso; o v4 sofre mais.
Hipótese ainda não testada sobre o porquê: nos dados de treino, "produto seguido de ? ou ." aparece em mensagens que NÃO são pedido ("quanto custa o espetinho de carne?", "vcs tem cerveja?"), então o modelo pode ter aprendido que produto colado a um fim de frase deve ser ignorado.

**Experimento E (em andamento):** "gêmeos de pontuação": cada mensagem de treino ganha uma cópia com a pontuação mexida (sem fim de frase, sem vírgulas, sem nenhuma, fim de frase vira vírgula) e o MESMO gabarito, para o modelo aprender que a pontuação não muda o pedido. Gerador com `--gemeos`, 4.000 exemplos (2.000 pares). O endereço é preservado intacto nos gêmeos.

## Decisões técnicas
- **LoRA em bf16**, não QLoRA: o Qwen 1.5B ocupa ~3 GB e a GPU tem 16 GB; comprimir em 4 bits só vale se o modelo não couber.
- **Prompt curto no treino** ("Extraia o pedido da mensagem em JSON."): o cardápio é aprendido nos pesos, o que reduz tokens por chamada.
- **Só a resposta conta na nota do treino** (loss mascarada na instrução).
- Treino v1: 800 exemplos, 3 épocas, ~24 min na GPU local; perda de validação 0,0023.

## Limitações conhecidas
- Teste sintético e mensagens escritas à mão por uma única pessoa; ainda falta validar com mensagens de clientes de verdade.
- O modelo local ainda é mais lento que o Claude (3,4 s vs 1,5 s) porque a inferência não está otimizada.
- "coca" sozinha é ambígua (lata ou 2L); nos dados vira sempre lata.

## Próximos passos
- Avaliar o v2 no teste sintético e nas 40 mensagens reais.
- Escrever 20 mensagens novas como prova final.
- API FastAPI (`POST /extrair-pedido`), publicação no Hugging Face, README e artigo.
