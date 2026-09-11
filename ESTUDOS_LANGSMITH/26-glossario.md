# 26 · Vocabulário para ler evidências e defender decisões

[Índice](README.md) · [Anterior](25-desafios-gabarito.md) · [Próximo](27-fontes-e-validacao.md)

Use como consulta durante os labs. Para cada termo, tente apontar um exemplo concreto antes de decorar a definição. As distinções abaixo seguem o uso neste curso; campos com nomes parecidos em produtos diferentes podem ter semânticas distintas.

## Observar uma execução

| Termo | Significado útil | Exemplo ou cuidado |
|---|---|---|
| Observabilidade | Capacidade de investigar o comportamento usando sinais do sistema | Encontrar a operação responsável por uma resposta degradada |
| Log | Registro de um evento | Uma linha de `step_log`; não fornece sozinha toda a árvore de chamadas |
| Métrica | Medida calculada sobre uma população definida | Proporção de casos concluídos corretamente |
| Run | Uma operação registrada no LangSmith | `consultar_cardapio` no lab 01 |
| Span | Unidade de operação no vocabulário de tracing | A correspondência conceitual de run em OpenTelemetry |
| Trace | Conjunto de operações relacionadas de uma execução | Pedido do restaurante com suas chamadas filhas |
| Root / child run | Operação raiz / operação chamada dentro de outra | `pedido-restaurante` / `calcular_total` |
| `run_id` / `trace_id` | Identidade da operação / identidade do trace | Um trace reúne vários runs |
| Metadata / tags | Campos de contexto / rótulos de agrupamento | `scenario=medium` / `estudo` |
| Tracing project | Agrupamento de traces | `dcra-estudos` |
| Workspace | Contexto da conta em que ficam recursos e acessos | Confirmar workspace ao procurar um projeto |
| Flush | Concluir o envio pendente do cliente | O processo precisa aguardar a exportação antes de terminar |

Prática: [02](02-fundamentos-observabilidade.md), [04](04-primeiro-trace.md) e [07](07-falhas-latencia-retries.md). Referências: [conceitos de observabilidade](https://docs.langchain.com/langsmith/observability-concepts) e [instrumentação manual](https://docs.langchain.com/langsmith/annotate-code).

## Estado e continuidade do processo

| Termo | Significado útil | Exemplo ou cuidado |
|---|---|---|
| Thread | Correlação de várias execuções de um caso | Início, devolução e aprovação |
| `configurable.thread_id` | Identificador usado pelo checkpointer do grafo | Recupera a sequência de estados do caso |
| `metadata.thread_id` | Identificador de correlação na telemetria | Deve acompanhar também as operações filhas |
| Checkpoint / checkpointer | Estado salvo / componente que o armazena e recupera | Postgres no produto; memória nos labs |
| `interrupt` / `resume` | Pausa para entrada externa / retomada com essa entrada | Solicitar revisão e receber `APPROVE` |
| Reducer | Regra que combina atualizações de um campo do estado | União de evidências coletadas em paralelo |
| Fan-out / fan-in | Abrir trabalhos paralelos / reunir seus resultados | Os três coletores antes de `assess_risk` |
| Idempotência | Repetir uma operação sem multiplicar seu efeito pretendido | Cuidado com gravações antes de um `interrupt` |
| Context propagation | Transportar identidade e relação entre operações | `copy_context()` no lab 14; cabeçalhos entre serviços |
| Orphan span | Operação sem o vínculo esperado com seu pai | Worker que perde o contexto de tracing |

Prática: [06](06-threads-checkpoints-revisao.md), [08](08-instrumentacao-contexto.md) e [17](17-reprodutibilidade-prompts.md). Referências: [threads no LangSmith](https://docs.langchain.com/langsmith/threads), [interrupts no LangGraph](https://docs.langchain.com/oss/python/langgraph/interrupts) e [contexto no OpenTelemetry](https://opentelemetry.io/docs/concepts/context-propagation/).

## Avaliar qualidade

| Termo | Significado útil | Exemplo ou cuidado |
|---|---|---|
| Dataset / example | Coleção de casos / um caso | As 16 linhas de `dados/casos.jsonl` |
| Reference output | Resposta esperada, destinada ao avaliador | Categoria e necessidade de revisão anotadas no caso |
| Target | Componente ou sistema que está sendo avaliado | O grafo com dependências fixture no lab 06 |
| Evaluator | Função ou procedimento que aplica um critério | `risk_correct` compara categoria com referência |
| Experiment | Resultados de uma versão avaliada em um dataset | Rodada da baseline ou da candidata |
| Baseline / candidate | Referência de comparação / versão proposta | Adaptador normal / mutação HIGH→LOW |
| Offline evaluation | Avaliação sobre exemplos fora do tráfego vivo | Pode rodar remotamente e chamar modelos |
| Online evaluation | Avaliação ligada às execuções observadas em uso | Examinar recomendações que chegam a um projeto |
| Fixture | Dependência controlada para um cenário conhecido | Parser determinístico substituindo o LLM |
| Slice / split | Recorte de análise / partição com finalidade definida | Casos HIGH / conjunto reservado para teste |
| Leakage | Informação da resposta esperada chega indevidamente ao target ou ao ajuste | Entregar o gabarito ao modelo durante o benchmark |
| Feedback | Nota ou comentário associado a um resultado | Lab 04 cria feedback calculado em código |
| Annotation queue | Fila organizada para revisão de resultados | Anotadores usam critérios explícitos |
| Rubrica | Definição dos critérios e de como pontuá-los | Separar `grounded` de `non_binding` |
| LLM-as-judge | Modelo usado como avaliador | Sua concordância e suas falhas também precisam de medição |
| Pairwise evaluation | Comparação entre duas respostas | Preferência com ordem controlada e motivo registrado |
| Groundedness | Sustentação das afirmações pelas evidências disponíveis | Citar uma fonte sem apoio para o número continua sendo falha |
| Schema validity | Conformidade com a estrutura exigida | JSON válido pode conter a coluna errada |
| Semantic correctness | Correspondência ao significado esperado | Identificar a operação e o alvo do pedido |

Prática: [10](10-feedback-anotacao.md) a [16](16-avaliar-workflow-agentes.md). Referências: [conceitos de avaliação](https://docs.langchain.com/langsmith/evaluation-concepts), [avaliar aplicações](https://docs.langchain.com/langsmith/evaluate-llm-application) e [gerenciar datasets](https://docs.langchain.com/langsmith/manage-datasets-programmatically).

## Interpretar medidas

| Termo | Significado útil | Exemplo ou cuidado |
|---|---|---|
| Accuracy / acerto | Proporção de respostas corretas no conjunto contado | `13/16` para a categoria da candidata com bug |
| Recall HIGH | Fração dos HIGH de referência identificados como HIGH | Denominador são os HIGH reais; neste lab, três |
| Falso negativo | Caso positivo que o detector deixa passar | HIGH classificado como LOW |
| Falso positivo (do juiz) | Alegação sem sustentação aceita como sustentada | j02 e j05 no juiz simulado; é o erro que deixa uma resposta ruim passar |
| Completude / cobertura | Quanto do trabalho esperado foi executado ou observado | Duas avaliações válidas entre seis previstas |
| Denominador vazio | Nenhum caso elegível para a medida | Recall HIGH ausente quando não há HIGH de referência |
| p50 / p95 | Percentis de uma distribuição de medidas | Exigem janela, população e volume conhecidos |
| Caminho crítico | Sequência que determina o tempo de término | Coletores paralelos não têm suas durações simplesmente somadas |
| Tempo próprio (*self time*) | Duração de um run fora do intervalo ocupado por seus filhos | Somar filhos concorrentes pode zerar o custo aparente da orquestração |
| Nearest-rank | Método de percentil que devolve uma observação existente | Com `n=1`, p50 e p95 são a mesma medição |
| Retry / fallback | Nova tentativa / resposta alternativa diante da falha | Recuperação pode acrescentar latência ou preservar degradação |
| Sampling | Seleção de parte das observações | Guardar mais erros distorce a média simples da amostra |
| SLI / SLO | Indicador de serviço / objetivo para o indicador | Taxa de conclusão e meta em uma janela definida |
| Quality gate | Política de aceitação aplicada às medidas | Recusar perda de revisão dos casos HIGH |
| Test tracking | Envio de exemplos, saídas e feedback de uma suíte de testes à plataforma | `LANGSMITH_TEST_TRACKING=false` desliga; é separado do tracing |

Prática: [07](07-falhas-latencia-retries.md), [12](12-evals-deterministicos.md), [19](19-privacidade-amostragem.md), [22](22-operacao-slos-incidentes.md) e [23](23-ci-gates.md). As fórmulas deste curso estão nos [avaliadores locais](labs/_evaluators.py).

## Custo e reconstrução do experimento

| Termo | Significado útil | Exemplo ou cuidado |
|---|---|---|
| Token usage | Quantidade de tokens registrada | Campo ausente não equivale a uso zero |
| Cached input | Parte da entrada atendida pelo cache | É subconjunto da entrada no lab 09 |
| Cost attribution | Atribuir custo às operações/casos responsáveis | Evitar somar custos agregados de pais e filhos |
| Budget enforcement | Recusar trabalho que ultrapassaria uma política de gasto | `Budget.reserve` é uma simulação local |
| Custo por sucesso | Custo dividido pelos casos concluídos segundo o critério de sucesso | Reduzir custo por request pode piorar esse indicador |
| Retention tier | Faixa de retenção de um trace, base ou estendida | A ingestão conta todo trace; a promoção é um evento cobrado à parte, só por feedback via API com extensão pedida, avaliador ou regra com a opção ligada |
| Exportação idempotente | Reexecutar a exportação da mesma identidade não duplica registros | `novos: 0, ja_presentes: 11` e o mesmo SHA-256 no lab 17; outra identidade exige outro diretório |
| Snapshot | Versão dos dados fixada para uma avaliação | O `as_of` utilizado para ler exemplos |
| Hash / commit | Identificador de conteúdo / revisão versionada | O hash não substitui armazenar os arquivos correspondentes |
| Tag / alias mutável | Nome que pode apontar para revisões diferentes | `prod` ou `latest` exige registrar a revisão resolvida |
| Provenance / manifesto | Origem e condições do resultado / registro dessas condições | Código, dados, versões, avaliadores e alterações locais |
| Replay / repeatability | Reexecutar / obter comportamento comparável nas condições definidas | Repetir uma chamada de modelo não garante texto idêntico |

Prática: [09](09-tokens-custos-orcamentos.md) e [17](17-reprodutibilidade-prompts.md). Referências: [cost tracking](https://docs.langchain.com/langsmith/cost-tracking) e [prompts pelo SDK](https://docs.langchain.com/langsmith/manage-prompts-programmatically).

## Recuperação e outras ferramentas

| Termo | Significado útil | Exemplo ou cuidado |
|---|---|---|
| RAG | Recuperar contexto para apoiar a resposta | Lab 11 usa dois documentos e respostas fixture |
| Retrieval / generation | Buscar evidências / produzir resposta usando o contexto | Falhas diferentes pedem correções diferentes |
| Observation / generation no Langfuse | Operação observada / operação de modelo | Confira os campos antes de converter dados de outra ferramenta |
| OpenTelemetry / OTLP | APIs, SDKs e convenções de telemetria / protocolo de transporte | Instrumentação e transporte não são o dashboard |
| Collector / backend | Receber, processar e encaminhar telemetria / armazenar e permitir consultá-la | Responsabilidades podem ficar em componentes distintos |

Prática: [20](20-rag-fora-do-projeto.md) e [21](21-langfuse-otel.md). Referências: [instrumentação Langfuse](https://langfuse.com/docs/observability/sdk/instrumentation) e [OpenTelemetry no LangSmith](https://docs.langchain.com/langsmith/trace-with-opentelemetry).
