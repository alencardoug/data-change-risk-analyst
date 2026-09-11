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

## Levar para outros projetos — e onde o seu julgamento decide

A tabela **log / métrica / trace / eval / auditoria / checkpoint** deste capítulo é independente de ferramenta. Trocar LangSmith por Langfuse muda nomes de tela; não muda quais perguntas cada instrumento responde.

**Na plataforma de atendimento (Langfuse Cloud).** Refaça a tabela com os artefatos daquele projeto: **log** estruturado com `request_id`/`conversation_id` (sem texto de mensagem em INFO, por `OBSERVABILITY.md`); **métrica** em SQL sobre `ai_generations` e `messages` (`docs/metrics/v3_queries.sql`, a "baseline de graça" da Fase 0); **trace** = as observações de um turno automático (`n5.process_turn` → `rag.retrieve` → `ai.*` → `autonomy.decision` → `message.sent`); **eval** = rubrica 0/1/2 e `critical_checks` do `detalhamento_execucao.md` §6; **auditoria** = catálogo de eventos (`ai.draft_accepted`, `ai.draft_edited`, `conversation.taken_over`); **checkpoint** = o estado da conversa e a pendência autônoma (`opens_at`/`resolves_at`) no Postgres, que continua a fonte de verdade. A mini-investigação sem computador tem uma versão direta: "o cliente perguntou o preço, a resposta foi cordial e errada". Não há erro técnico; há erro de qualidade; o primeiro span a abrir é `rag.retrieve` (a query exata embedada e o rank do documento certo), e o caso vira item de dataset com `expected_facts` contendo o preço correto. Um juiz que só lê a resposta final talvez não veja que o documento certo nem chegou ao modelo.

**Em projetos comuns do ecossistema.** A regra **unidade, população, janela e critério** é a que mais falta em relatórios de projetos com LLM. "Acurácia 92%" sem dizer *sobre quais casos, de qual versão, medida por quem* não é uma medida; é uma frase. Em qualquer projeto, antes de aceitar um número, faça as quatro perguntas. Em Langfuse, isso se traduz em: qual `environment`, qual `release`, qual dataset run, qual score name — os quatro campos existem para carregar exatamente essa informação.

**O fator humano — onde a IA faz e onde você decide.** A IA calcula métricas, agrega traces e até sugere critérios de eval — e faz isso mais rápido que você. O que ela não faz é decidir **qual pergunta importa**. "A resposta foi útil para um paciente com medo esperando retorno?" não é uma métrica que sai do trace; é um critério que uma pessoa que conhece o atendimento formula, e depois a IA pode ajudar a medir. Foque em formular o critério antes de olhar a ferramenta: escreva a pergunta em uma frase, com unidade e população, e só então pergunte a um assistente como medi-la. Se você começar pela ferramenta, ela vai lhe oferecer as métricas que já sabe calcular — tokens, latência, contagem de erros — e você vai medir o que é fácil em vez do que é importante. O prato bonito com o ingrediente errado só é detectado por quem sabe qual era o ingrediente.
