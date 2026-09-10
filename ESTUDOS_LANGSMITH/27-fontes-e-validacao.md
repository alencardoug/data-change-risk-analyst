# 27 · Fontes, versões e o que foi realmente verificado

[Índice](README.md) · [Anterior](26-glossario.md) · [Próximo](28-caderno-de-evidencias.md)

**Conferência: 9 de setembro de 2026.** Este registro distingue execução local, inspeção de API e leitura da documentação. A aprovação de testes com fixtures não valida autenticação, ingestão no SaaS ou qualidade de um modelo real.

## Fontes primárias consultadas

| Assunto | Fonte oficial | O que sustenta no curso |
|---|---|---|
| Estrutura de observabilidade | [Observability concepts](https://docs.langchain.com/langsmith/observability-concepts) | Distinção entre runs, traces, threads e projetos |
| Instrumentação Python | [Custom instrumentation](https://docs.langchain.com/langsmith/annotate-code) | `traceable`, contexto de tracing, IDs e finalização do envio |
| Correlação de casos | [Configure threads](https://docs.langchain.com/langsmith/threads) | Metadados de thread e propagação aos filhos |
| Continuidade do grafo | [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) | Checkpointer, `thread_id` e retomada com `Command` |
| Modelo de avaliação | [Evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts) | Datasets, referências, experimentos e técnicas de avaliação |
| Execução de avaliações | [How to evaluate agents](https://docs.langchain.com/langsmith/evaluate-llm-application) | Target, avaliadores, concorrência e repetições |
| Datasets pelo SDK | [Manage datasets programmatically](https://docs.langchain.com/langsmith/manage-datasets-programmatically) | Exemplos e versões usadas para comparar rodadas |
| Tokens e custos | [Cost tracking](https://docs.langchain.com/langsmith/cost-tracking) | `usage_metadata`, detalhes de cache e custos explícitos |
| Versões de prompt | [Manage prompts programmatically](https://docs.langchain.com/langsmith/manage-prompts-programmatically) | Publicação e recuperação usando o SDK `langsmith` |
| Juiz online | [LLM-as-a-judge online evaluators](https://docs.langchain.com/langsmith/online-evaluations-llm-as-judge) | Filtros, sampling, limites de gasto e efeito na retenção |
| Dados exportados | [Prevent logging of sensitive data](https://docs.langchain.com/langsmith/mask-inputs-outputs) | Ocultação e processamento das entradas/saídas do trace |
| Langfuse | [SDK instrumentation](https://langfuse.com/docs/observability/sdk/instrumentation) | `start_as_current_observation`, operações filhas e `flush` |
| OpenTelemetry no LangSmith | [Trace with OpenTelemetry](https://docs.langchain.com/langsmith/trace-with-opentelemetry) | Integração de tracing e configuração de exportação |
| Contexto distribuído | [OpenTelemetry context propagation](https://opentelemetry.io/docs/concepts/context-propagation/) | Relação entre contexto, spans e fronteiras de serviços |

As fontes descrevem capacidades das ferramentas. A interpretação didática e os exemplos vêm dos scripts deste repositório. Navegação, planos, preços e ofertas podem mudar; confirme esses detalhes na documentação e no workspace quando executar uma etapa remota. Nenhuma tabela de preços reais foi validada: os números do lab 09 são fictícios.

## Ambiente local conferido

As versões abaixo foram lidas do ambiente instalado, sem atualizar dependências:

| Componente | Versão |
|---|---|
| Python | 3.13.14 |
| `langsmith` | 0.11.1 |
| `langchain` | 1.3.18 |
| `langgraph` | 1.2.11 |
| `langchain-core` | 1.6.1 |
| `langchain-openai` | 1.6.0 |
| `langgraph-checkpoint-postgres` | 3.1.2 |
| `pydantic` | 2.13.4 |
| `pytest` | 9.1.1 |
| `ruff` | 0.16.5 |

O ponto de partida do código foi o commit `533b72d4a7f29e5892bbd491e60f6cb2b4a5f288`, com os capítulos finais acrescentados na árvore de trabalho. Para sua execução, gere um novo `artefatos/manifesto.json` com [00_doctor.py](labs/00_doctor.py) e preserve o código/dados correspondentes. Esse manifesto registra versões e hashes; não inclui os valores do `.env`.

O SDK Langfuse não foi instalado no ambiente do produto. O lab 15 tem ensaio local sem essa dependência; o comando para um ambiente separado está no [capítulo 21](21-langfuse-otel.md).

## APIs inspecionadas

Foi verificada por introspecção a presença dos métodos e parâmetros utilizados na versão instalada. Isso detecta incompatibilidades básicas de assinatura, mas não substitui executar uma chamada autenticada ao serviço.

| Superfície | Uso no material | Nível de verificação |
|---|---|---|
| `traceable`, `tracing_context` | Instrumentação, metadados, hierarquia e modo local | Execução local e testes que inspecionam runs em memória |
| `Client.create_examples`, `list_examples(as_of=...)`, `read_dataset_version` | Criar casos e fixar a versão do dataset | Assinaturas locais e documentação; sem publicação remota |
| `Client.evaluate` | Avaliadores, `max_concurrency`, `num_repetitions` | Assinatura local; adaptação de `reference_outputs` testada sem rede |
| `Client.create_feedback` | Nota de código ligada ao run | Assinatura local, incluindo `feedback_source_type`; sem envio |
| `Client.push_prompt`, `pull_prompt`, `pull_prompt_commit` | Publicação privada e recuperação por commit | Assinaturas locais, incluindo `skip_cache`; renderização dos prompts testada localmente |
| `Client.flush(timeout=...)`, `get_run_url` | Finalização e URL do trace | Assinaturas locais; sem ingestão nem obtenção de URL autenticada |
| `RunTree.set(usage_metadata=...)` | Uso e custo sintéticos | Parâmetro presente; contabilidade testada localmente; sem renderização na UI |
| Processadores de inputs/outputs | Redação dos campos registrados | Teste local compara trace processado com retorno original da função |
| Langfuse `start_as_current_observation`, `flush` | Lab opcional de outra ferramenta | Conferência na documentação oficial; modo remoto não executado |

## Validação executada

O [verificador do material](verificar_material.py) tem duas partes: links/sintaxe/dados e execução dos comandos locais. Para repetir ambas na raiz do repositório:

```bash
.venv/bin/python ESTUDOS_LANGSMITH/verificar_material.py
```

Ele roda **25 comandos**, cobrindo os **16 scripts numerados** e as variantes de casos, revisão e gate. Bloqueia chamadas de conexão/resolução via `socket` nos subprocessos e falha se detectar tentativa de rede, mesmo que o laboratório a capture. Isso é uma verificação desses comandos e caminhos Python, sem afirmar isolamento universal de qualquer código futuro.

| Verificação | Resultado |
|---|---|
| Links locais, sintaxe dos labs e JSON/JSONL | 30 documentos com destinos locais existentes; arquivos Python e dados válidos |
| Modos locais dos laboratórios | 25 comandos com exit codes esperados; nenhuma tentativa de rede detectada |
| Avaliação determinística | Baseline: 16/16 categorias; candidata: 13/16; recall HIGH da candidata: 0/3 |
| Gate local | Baseline termina em 0; mutação termina em 1, como esperado |
| Testes do produto e curso, exceto o arquivo de subprocesso MCP | 65 aprovados, 19 pulados; inclui os 10 casos de teste do curso |
| Testes de subprocesso MCP, executados separadamente | 2 aprovados fora do sandbox |
| `uv run ruff check src tests` | Aprovado |

Os testes foram executados com `DATABASE_URL` vazio, `RUN_LLM_TESTS=0` e tracing desativado. Os 19 skips correspondem a **15 testes que precisam de Postgres** e **4 testes opt-in com LLM**. O pytest emite seis avisos de depreciação de `ast.Str` no adaptador de avaliadores do SDK LangSmith instalado; eles não impediram os testes.

A primeira execução completa ficou parada em `tests/mcp/test_mcp_usage_tool.py`. A repetição isolada, com timeout, também não terminou no sandbox. Esses dois testes passaram fora dele em 13,56 segundos. O resultado agregado é **67 testes aprovados e 19 pulados**, obtido em duas execuções; não se trata de uma suíte completa aprovada dentro do sandbox. O código do produto não foi alterado para contornar essa limitação.

Para repetir a divisão utilizada:

```bash
env DATABASE_URL= RUN_LLM_TESTS=0 LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false uv run pytest tests ESTUDOS_LANGSMITH/tests --ignore=tests/mcp/test_mcp_usage_tool.py
env DATABASE_URL= RUN_LLM_TESTS=0 LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false uv run pytest tests/mcp/test_mcp_usage_tool.py
uv run ruff check src tests
```

Na sessão de validação também foram definidos `UV_OFFLINE=1`, `UV_FROZEN=1` e um cache em `/tmp`, usando o ambiente já instalado. A segunda linha acima deve rodar em um ambiente que permita o subprocesso MCP. Esses comandos não solicitam os testes de banco ou modelo real.

## O que ficou sem execução remota

Nesta conferência, não foram executados envios de traces, feedback, datasets, experimentos ou prompts ao LangSmith; chamadas de modelo real dos labs 02/07/08; juízes online, filas de anotação e ações na UI; nem envio ao Langfuse ou um pipeline OpenTelemetry entre serviços.

Consequentemente, o curso não fornece URLs privadas inventadas, notas de juiz presumidas, autenticação supostamente aprovada ou custos reais medidos. Os comandos dessas etapas estão nos capítulos correspondentes para execução na conta do aluno. Ao realizá-las, registre resultados e limitações no [caderno de evidências](28-caderno-de-evidencias.md).
