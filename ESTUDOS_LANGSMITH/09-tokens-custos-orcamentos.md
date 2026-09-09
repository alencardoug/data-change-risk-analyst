# 09 · O agente não paga a conta; você precisa entendê-la

[Índice](README.md) · [Anterior](08-instrumentacao-contexto.md) · [Próximo](10-feedback-anotacao.md)

**Objetivo:** fazer contas corretas e distinguir medir de limitar gasto. Tempo: 25–30 minutos. Código: [09_costs.py](labs/09_costs.py).

## Primeiro, separe as contas

| Parcela | Exemplos |
|---|---|
| Modelo da aplicação | interpretação, recomendação, turnos do investigador |
| Avaliação | juiz LLM, repetições de targets, eventualmente modelos diferentes |
| Ferramentas | busca paga, consultas/serviços com preço por chamada |
| Infraestrutura | Cloud Run, banco, armazenamento, rede |
| Observabilidade | ingestão, retenção e recursos do plano |

O custo calculado em um span de modelo não é automaticamente o custo total do caso nem a fatura final. LangSmith pode calcular valores a partir de uso e tabela de preços ou receber custos explícitos. Integração, identificação do modelo e informação de uso precisam estar corretas. [Cost tracking](https://docs.langchain.com/langsmith/cost-tracking).

## Conta de guardanapo — números inventados

Rode:

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/09_costs.py
```

Tabela **FICTÍCIA**: US$2 por milhão de tokens de entrada sem cache; US$0,50 por milhão de entrada lida do cache; US$8 por milhão de saída.

Uma chamada tem 1.000 tokens de entrada, dos quais 200 vieram do cache, e 200 de saída:

```text
entrada sem cache = (1.000 − 200) × 2 / 1.000.000 = US$0,0016
entrada com cache = 200 × 0,50 / 1.000.000         = US$0,0001
saída             = 200 × 8 / 1.000.000            = US$0,0016
total                                                  US$0,0033
```

Os 200 tokens de cache já estão dentro dos 1.000 de entrada. Somá-los como tokens adicionais contaria parte do uso duas vezes. O exemplo verifica também entradas inválidas, como cache maior que input.

O script monta um caso com três custos de folhas: **US$0,02195**. A soma errada de raiz agregada, wrapper do investigador e folhas dá **US$0,05470**. A diferença é dupla contagem, não uma taxa misteriosa.

## Veja os campos na UI, sem chamar modelo

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/09_costs.py --send
```

Abra o projeto **`dcra-estudos-custos-sinteticos`**. O exemplo envia uso e custo inventados identificados como tal. Procure `modelo-de-papel`, `usage_metadata` e os detalhes de entrada/cache/saída. Isso ensina o formato de medição; não representa execução ou preços de um provedor real.

Para medir de verdade, use o modo real do lab 02 e abra os spans de modelo. Campo ausente ou modelo sem correspondência de preço não autoriza concluir “custou zero”. Use os [metadados padronizados de modelo](https://docs.langchain.com/langsmith/ls-metadata-parameters) e confira a tabela correspondente ao período e à configuração da conta.

## Quanto custa uma avaliação?

Considere 16 exemplos × 2 versões × 3 repetições: **96 execuções de target**. Com um juiz por resultado: mais **96 execuções de juiz**. Se cada target tiver dois passos de modelo, já são 192 chamadas lógicas da aplicação antes dos juízes e retries.

Fórmula de planejamento:

```text
C_eval ≈ N × V × R × (C_target + J × C_juiz)
```

`N`: exemplos; `V`: variantes; `R`: repetições; `J`: juízes por resultado. Não multiplique também por concorrência: concorrência muda quantas execuções ocorrem ao mesmo tempo, não o número planejado de exemplos.

## Medidor, alarme e disjuntor

Um painel é o medidor. Um alerta de orçamento é o alarme. Um mecanismo que recusa uma próxima operação é o disjuntor. Não são garantias equivalentes.

O lab tem `Budget.reserve`: com US$0,010 fictício, aceita três reservas de US$0,0033 e recusa a quarta. É um exemplo local de admissão antes da execução. Em produção, precisa de estimativa conservadora, reconciliação com gasto observado e reserva atômica compartilhada entre workers. Também precisa considerar resposta em andamento, retries e cobrança de ferramentas.

`max_concurrency=1`, limite de recursão e `--limit 3` ajudam a controlar execução, mas nenhum deles, isoladamente, é teto financeiro. Os limites de gasto de **avaliadores gerenciados** do LangSmith têm seu próprio escopo, tratado em [18](18-evals-online-producao.md).

**Pergunta de entrevista:** “Como reduziria custo?” Meça a parcela dominante, compare qualidade antes/depois, reduza contexto redundante, evite investigação sem benefício, limite repetições e avalie roteamento de modelo/cache com critérios explícitos. O objetivo útil pode ser **custo por caso resolvido corretamente**, e não só custo por requisição.

**Memorize:** *token usage*, *cost attribution*, *cached input*, *budget enforcement*, *cost per successful task*.
