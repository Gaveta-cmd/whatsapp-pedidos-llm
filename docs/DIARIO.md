# Diário do projeto: LLM que extrai pedidos de WhatsApp

Atualizado em 30/10/2026. Material de apoio para o README e para o post. Todos os números vêm de
`outputs/resultados/*.json`; as imagens são geradas por `python src/gerar_evidencias.py`.

## Evidências (docs/evidencias/)
- `01_comparacao_modelos.png`: gráfico de acerto, JSON válido e latência (`src/gerar_evidencias.py`)
- `02_terminal_testes.png`: 19 testes automáticos passando
- `03_erros_modelo_v1.png`: onde o modelo v1 errou nas mensagens escritas à mão (JSON inválido, "1 de cada", "capricha")
- `04_terminal_resultados.png`: tabela de resultados
- `05_prova_final.png`: prova final com 20 mensagens novas (modelo treinado vs Claude)
- `06_erros_prova_final.png`: principais erros do modelo na prova final
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
