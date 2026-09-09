# 02 · Observar, avaliar e auditar são perguntas diferentes

[Índice](README.md) · [Anterior](01-mapa-do-projeto.md) · [Próximo](03-preparacao.md)

**Objetivo:** entender o problema antes de decorar a ferramenta. Tempo: 15–20 minutos.

Você recebe uma reclamação: “a análise veio errada e demorou”. Um log com `request finished, 200 OK` informa que houve uma resposta. Ainda falta descobrir se o modelo interpretou a coluna errada, se uma fonte ficou indisponível, se o investigador repetiu buscas ou se a pessoa simplesmente levou vinte minutos para aprovar.

| Instrumento | Pergunta | Exemplo DCRA |
|---|---|---|
| Log | Que evento foi registrado? | `finalize: APPROVED` |
| Métrica | Quanto/quantas vezes, em uma população e janela? | p95 de latência de interpretação por versão |
| Trace | Que etapas compuseram esta execução? | interpretação → coletores → recomendação |
| Eval | O resultado ou processo atende ao critério? | coluna extraída correta; HIGH não tratado como LOW |
| Auditoria de negócio | Quem decidiu o quê, sobre quais evidências? | revisor, nota e decisão no `AnalysisRecord` |
| Checkpoint | De onde o workflow pode continuar? | estado anterior à resposta ao `interrupt()` |

**Observabilidade** é a capacidade de compreender o comportamento interno por sinais acessíveis. Não equivale a “instalei um painel”. Você precisa de instrumentação útil, correlação e perguntas que possam ser respondidas. Os traces fornecem a estrutura de etapas; LangSmith organiza runs, hierarquias e metadados para examiná-la. [Conceitos de observabilidade](https://docs.langchain.com/langsmith/observability-concepts).

## A cozinha e o crítico gastronômico

O trace mostra que o cozinheiro fritou o alho por dez minutos. A avaliação diz que o prato ficou queimado. O relatório de venda registra que o cliente recebeu o prato. Nenhuma dessas evidências substitui todas as outras.

Agora o caso mais traiçoeiro: o prato chega bonito, no prazo, e com o ingrediente errado. Em IA isso acontece com frequência suficiente para tornar “não deu exception” um critério muito fraco. A saída pode ser JSON válido, latência baixa e conteúdo semanticamente errado.

Uma eval torna o critério explícito. Pode comparar um identificador exatamente, conferir uma regra, pedir julgamento humano ou usar um modelo como juiz. O uso de um LLM para pontuar também introduz um componente falível. [Conceitos de avaliação](https://docs.langchain.com/langsmith/evaluation-concepts).

## Trace, run, span, thread

- **Run:** uma execução instrumentada de uma operação; pode ser pai ou filho.
- **Root run:** o run superior de uma execução instrumentada.
- **Trace:** a árvore relacionada de runs, começando numa raiz.
- **Span:** termo comum em tracing distribuído; unidade análoga de trabalho com início, fim e contexto. Não assuma identidade de schema entre todos os produtos.
- **Thread:** agrupamento de execuções relacionadas, como as idas e voltas do mesmo caso. Não significa thread de sistema operacional.

O [modelo de traces do OpenTelemetry](https://opentelemetry.io/docs/concepts/signals/traces/) ajuda a transferir a ideia para outras ferramentas: você procura operações, relações e tempos, mesmo quando os nomes na interface mudam.

## Mini-investigação sem computador

Considere este relato:

```text
Pedido: remover orders.customer_legacy_id
interpretação: DROP_COLUMN orders.customer_id
coletores: todos responderam normalmente
risco: MEDIUM
recomendação: bem escrita
HTTP: 200
```

Responda antes de prosseguir:

1. Há erro técnico obrigatório? Não; todas as chamadas podem ter completado.
2. Há erro de qualidade? Sim: o alvo da mudança foi interpretado incorretamente.
3. Qual span abrir primeiro? A interpretação, comparando texto cru e estrutura extraída.
4. Que caso adicionar ao dataset? A solicitação original com `target_column=customer_legacy_id` como referência revisada.
5. Um juiz que só lê a recomendação resolveria? Talvez nem veja a troca de coluna. O avaliador precisa receber a informação necessária ao critério.

**Regra para memorizar:** a medição precisa de **unidade, população, janela e critério**. “Qualidade 95%” é incompleto. “95% de correspondência do alvo em 80 pedidos de português, dataset v3, nesta versão do parser” permite uma conversa técnica.

**Pergunta de entrevista:** “Por que tracing não basta?” Resposta: ele revela como uma execução aconteceu; critérios e referências permitem julgar se o comportamento foi aceitável. Juntos, ajudam a transformar falhas observadas em testes de regressão.
