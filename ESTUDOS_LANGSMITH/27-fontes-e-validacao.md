# 27 · Fontes, versões e o que foi realmente verificado

[Índice](README.md) · [Anterior](26-glossario.md) · [Próximo](28-caderno-de-evidencias.md)

**Conferência: 9 de setembro de 2026; revisões: 10 e 11 de setembro de 2026.** Este registro distingue execução local, inspeção de API e leitura da documentação. A aprovação de testes com fixtures não valida autenticação, ingestão no SaaS ou qualidade de um modelo real.

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
| Avaliação como testes | [Integração com pytest](https://docs.langchain.com/langsmith/pytest) | `@pytest.mark.langsmith`, `log_inputs/outputs/reference_outputs/feedback` e o controle `LANGSMITH_TEST_TRACKING` |
| Painéis nativos | [Dashboards](https://docs.langchain.com/langsmith/dashboards) | Existência de painéis pré-construídos e personalizados; disponibilidade a confirmar na conta |
| Retenção e cobrança | [Administration overview](https://docs.langchain.com/langsmith/administration-overview) e [preços](https://www.langchain.com/pricing) | Faixas de retenção, promoção de traces e franquias; nenhum número foi copiado para o material |
| Saída dos dados | [Data export](https://docs.langchain.com/langsmith/data-export) | Bulk export em Parquet para bucket S3; Enterprise para contas criadas após 3 de agosto de 2026 (Plus até 1º de fevereiro de 2027 para contas anteriores); não executado |
| Janela de consulta | [Trace query syntax](https://docs.langchain.com/langsmith/trace-query-syntax) | `and(gte(start_time, "…Z"), lt(start_time, "…Z"))`, usado pelo lab 17 no modo `--send` |
| Modelo de cobrança e promoção de retenção | [Administration overview](https://docs.langchain.com/langsmith/administration-overview) (seções *billing model* e *data retention auto-upgrades*) | Dois medidores na fatura (ingestão e upgrades); o que promove um trace e o que não promove |
| Uso do app publicado | [DEPLOYMENT.md](../DEPLOYMENT.md), [schema.sql](../src/dcra/persistence/schema.sql) e [nodes.py](../src/dcra/graph/nodes.py) do próprio produto | Onde cada análise é gravada, quando (`finalize`) e como ligar o tracing em produção; capítulo 29 |

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
| `Client.evaluate` | Avaliadores, `summary_evaluators`, `max_concurrency`, `num_repetitions` | Assinatura local; adaptação de `reference_outputs` e do avaliador de resumo testada sem rede |
| `Client.create_feedback` | Nota de código ligada ao run | Assinatura local, incluindo `feedback_source_type`; sem envio |
| `Client.push_prompt`, `pull_prompt`, `pull_prompt_commit` | Publicação privada e recuperação por commit | Assinaturas locais, incluindo `skip_cache`; renderização dos prompts testada localmente |
| `Client.flush(timeout=...)`, `get_run_url` | Finalização e URL do trace | Assinaturas locais; sem ingestão nem obtenção de URL autenticada |
| `Client.list_runs(filter=..., is_root=..., error=...)` | Agregação de runs no lab 16 | Assinatura e sintaxe de filtro lidas na docstring instalada; consulta remota não executada |
| `RunTree.set(usage_metadata=...)` | Uso e custo sintéticos | Parâmetro presente; contabilidade testada localmente; sem renderização na UI |
| Processadores de inputs/outputs | Redação dos campos registrados | Teste local compara trace processado com retorno original da função |
| Langfuse `start_as_current_observation`, `flush` | Lab opcional de outra ferramenta | Conferência na documentação oficial; modo remoto não executado |
| `@pytest.mark.langsmith`, `langsmith.testing.log_*` | Suíte `evals/` | Código do decorador lido no SDK: a decisão de rastrear é tomada na importação do módulo, por `LANGSMITH_TEST_TRACKING`; modo local executado 3× em teste, sem rede; modo remoto não executado |
| `Client.list_feedback(run_ids=...)`, `list_runs(filter=..., limit=...)` | Lab 17, modo `--send` | Assinaturas locais; filtro, teto (`max + 1`) e normalização testados com cliente falso; consulta remota não executada |
| `psycopg.connect(...)` com `read_only = True`, JSONB (`->-1`, `->>`, `@>`), `percentile_cont` | Lab 18 | Executado contra um Postgres 16 local (`docker compose`) com 28 registros de desenvolvimento e 3 inseridos pelo teste; produção (Neon) não consultada |

## Validação executada

O [verificador do material](verificar_material.py) tem duas partes: links/sintaxe/dados e execução dos comandos locais. Para repetir ambas na raiz do repositório:

```bash
.venv/bin/python ESTUDOS_LANGSMITH/verificar_material.py
```

Ele roda **38 comandos**, cobrindo os **19 scripts numerados**, as variantes de casos, revisão e gate, o juiz simulado com e sem falha, a exportação executada duas vezes mais as duas recusas (identidade diferente e teto), e a suíte pytest de avaliação nas duas variantes, com subconjunto reprovado pelo gate e aceito com `--parcial`. O lab 18 entra só no modo que imprime o SQL; o modo `--db` é coberto pelo teste com banco. Bloqueia chamadas de conexão/resolução via `socket` nos subprocessos e falha se detectar tentativa de rede, mesmo que o laboratório a capture. Isso é uma verificação desses comandos e caminhos Python, sem afirmar isolamento universal de qualquer código futuro.

| Verificação | Resultado |
|---|---|
| Links locais, sintaxe dos labs e JSON/JSONL | 33 documentos com destinos locais existentes; arquivos Python e dados válidos |
| Modos locais dos laboratórios | 38 comandos com exit codes esperados; nenhuma tentativa de rede detectada |
| Avaliação determinística | Baseline: 16/16 categorias; candidata: 13/16; recall HIGH da candidata: 0/3 |
| Gate local | Baseline termina em 0; mutação termina em 1, como esperado |
| Suíte pytest `evals/` | Baseline: 17 aprovados, exit 0; mutação: c03, c04, c07 e o teste de conjunto falham, exit 1; `-k c01` termina em 1 pelo gate de completude e em 0 com `--parcial`; relatório igual ao do lab 06 e com hashes de `evals/` no manifesto |
| Juiz simulado | 4/6 conjunta; `grounded` com 2 falsos positivos (j02, j05); com falha simulada em j04: cobertura 5/6, 3/5, exit 1 |
| Exportação por SDK, modo local | 11 runs e 3 feedbacks na janela; 3 runs fora; segunda execução sem registros novos e com o mesmo SHA-256; outra identidade no mesmo diretório e excesso sobre o teto terminam em 1 sem gravar |
| Testes do produto e do curso, `tests ESTUDOS_LANGSMITH/tests`, 11 de setembro de 2026, **sem** banco | 82 aprovados, 20 pulados em uma execução; inclui os 2 de subprocesso MCP e os 26 do curso |
| Os mesmos testes **com** Postgres local (`docker compose up -d postgres`) | 98 aprovados, 4 pulados (só os opt-in com modelo real); os 15 testes de banco do produto e o teste do lab 18 executados |
| Histórico: 9–10 de setembro, exceto o arquivo de subprocesso MCP | 67 aprovados, 19 pulados, com 12 casos do curso; os 2 testes MCP aprovados à parte, fora do sandbox |
| `uv run ruff check src tests ESTUDOS_LANGSMITH` | Aprovado |

Os testes foram executados com `DATABASE_URL` vazio, `RUN_LLM_TESTS=0` e tracing desativado. Os 19 skips correspondem a **15 testes que precisam de Postgres** e **4 testes opt-in com LLM**. O pytest emite seis avisos de depreciação de `ast.Str` no adaptador de avaliadores do SDK LangSmith instalado; eles não impediram os testes.

A primeira execução completa ficou parada em `tests/mcp/test_mcp_usage_tool.py`. A repetição isolada, com timeout, também não terminou no sandbox. Esses dois testes passaram fora dele em 13,56 segundos. O resultado agregado é **69 testes aprovados e 19 pulados**, obtido em duas execuções; não se trata de uma suíte completa aprovada dentro do sandbox. O código do produto não foi alterado para contornar essa limitação.

Na revisão de 10 de setembro de 2026 foram reexecutados os 67 testes fora do arquivo MCP, agora incluindo os dois casos novos do curso, mais o verificador e o `ruff`. O arquivo de subprocesso MCP **não** foi reexecutado nessa revisão: os 2 testes que ele contém seguem contados a partir da sessão anterior, e nada foi alterado em `src/` nem em `tests/mcp/` desde então.

Na revisão de 11 de setembro de 2026, fora do sandbox, a suíte completa `tests ESTUDOS_LANGSMITH/tests` terminou com **82 aprovados e 20 pulados** sem banco, e com **98 aprovados e 4 pulados** com o Postgres local do `docker-compose.yml` — a primeira vez que os 15 testes de banco do produto foram executados nesta série de revisões. Os **26 casos de teste do curso** incluem catorze novos: juiz simulado, exportação — janela, texto livre, identidade, teto e cliente falso —, estimativa de plataforma, seis sobre a suíte pytest (executada em subprocesso com rede bloqueada) e dois do lab 18, um dos quais só roda com banco local alcançável e é pulado sem ele. Uma revisão do Codex no mesmo dia apontou seis problemas — mistura de origens e teto silencioso na exportação, subconjunto aprovado pelo gate, manifesto sem os arquivos de `evals/`, cobrança e retenção simplificadas demais — corrigidos antes desta contagem. `uv run pytest` sozinho, que só cobre `tests/`, terminou com 57 aprovados e 19 pulados; `ruff` aprovado em `src tests ESTUDOS_LANGSMITH`. O código do produto em `src/` não foi alterado.

Para repetir a divisão utilizada:

```bash
env DATABASE_URL= RUN_LLM_TESTS=0 LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false uv run pytest tests ESTUDOS_LANGSMITH/tests --ignore=tests/mcp/test_mcp_usage_tool.py
env DATABASE_URL= RUN_LLM_TESTS=0 LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false uv run pytest tests/mcp/test_mcp_usage_tool.py
uv run ruff check src tests ESTUDOS_LANGSMITH
```

Na sessão de validação também foram definidos `UV_OFFLINE=1`, `UV_FROZEN=1` e um cache em `/tmp`, usando o ambiente já instalado. A segunda linha acima deve rodar em um ambiente que permita o subprocesso MCP. Esses comandos não solicitam os testes de banco ou modelo real.

## Métodos marcados como obsoletos no SDK instalado

A introspecção do `langsmith` 0.11.1 encontrou avisos de depreciação em três métodos usados pelo curso. Eles funcionam hoje; a remoção anunciada é **depois de 31 de janeiro de 2027**.

| Método usado | Onde | Substituto indicado pelo SDK |
|---|---|---|
| `Client.read_run` | [_common.py](labs/_common.py), ao imprimir a URL do trace | `Client.runs.retrieve` |
| `Client.get_run_url` | [_common.py](labs/_common.py), mesma função | `Client.runs.get_url` |
| `Client.list_runs` | [16_consultar_runs.py](labs/16_consultar_runs.py), modo `--send` | `Client.runs.query` |

O material permanece no caminho antigo de forma deliberada: o namespace `Client.runs` é assíncrono e sua primeira leitura chama `_check_backend_version`, exigindo backend `0.16` ou superior em instalação própria. Trocar agora acrescentaria plumbing assíncrono e uma dependência de versão sem ganho didático. Essa é a decisão registrada, não um descuido; o [capítulo 22](22-operacao-slos-incidentes.md) a explica ao aluno. Reveja-a antes de reaproveitar o código em algo que precise durar até 2027.

## O que ficou sem execução remota

Nesta conferência, não foram executados envios de traces, feedback, datasets, experimentos ou prompts ao LangSmith; chamadas de modelo real dos labs 02/07/08; juízes online, filas de anotação e ações na UI; nem envio ao Langfuse ou um pipeline OpenTelemetry entre serviços.

A revisão de 11 de setembro de 2026 acrescenta cinco itens do mesmo tipo: no capítulo 29, `gcloud logging read` não foi executado, nenhuma análise foi submetida ao app publicado (logo o projeto `dcra-prod` ainda não recebeu traces) e o banco de produção não foi consultado — já `create-secrets.sh` e `deploy.sh` **foram** executados nesse dia, com a revisão `dcra-00002-kcv` servindo 100% do tráfego e a configuração de tracing conferida no serviço; o modo remoto da suíte `evals/` (`DCRA_EVALS_REMOTE=1`), que criaria o dataset `dcra-evals-contratos` e um experimento por variante; o modo `--send` do lab 17, incluindo `list_feedback`; o exercício do painel nativo do capítulo 22, que não teve gráfico criado nem valor comparado; e o bulk export, que depende de plano. Todos estão escritos como procedimento, com a evidência a cargo de quem executar.

Acrescentam-se, na revisão de 10 de setembro de 2026, dois itens do mesmo tipo. O `summary_evaluators` do lab 06 teve a forma da função validada contra o normalizador do SDK em teste local, mas **nenhum experimento remoto foi publicado**: não há confirmação visual de como `high_risk_recall` aparece na comparação da UI. E o modo `--send` do lab 16 **não foi executado**: a assinatura e a sintaxe do filtro vêm da docstring instalada, e o modo local, esse sim verificado, não depende dela. Trate ambos como o lab 15 do Langfuse — o caminho está escrito, a confirmação é sua.

Consequentemente, o curso não fornece URLs privadas inventadas, notas de juiz presumidas, autenticação supostamente aprovada ou custos reais medidos. Os comandos dessas etapas estão nos capítulos correspondentes para execução na conta do aluno. Ao realizá-las, registre resultados e limitações no [caderno de evidências](28-caderno-de-evidencias.md).

## Levar para outros projetos — e onde o seu julgamento decide

Este capítulo é um registro do que foi **executado, inspecionado ou apenas lido** — três níveis de verificação que qualquer projeto com IA deveria distinguir, especialmente quando parte do trabalho foi feito por assistentes.

**Na plataforma de atendimento (Langfuse Cloud).** O projeto já pratica essa distinção: `LANGFUSE/validation-report.json`, `analysis.md §8` (prova LF-1 persistida no Cloud, com checkpoint datado), `app/tests/langfuse_cloud_verification.py` e `test_langfuse_probe.py`, e as frases do plano — "nada de Langfuse foi instrumentado no código" (2026-09-10), depois "checkpoint: prova LF-1 persistida", depois "continuação LF-2..LF-5 autorizada". Faça para ele a tabela deste capítulo: **executado** (probe LF-1 no Cloud; testes do adaptador; suíte com flag `false`), **inspecionado** (assinatura do SDK 4.15.1: `should_export_span`, `tracer_provider`, o `atexit` desregistrado — "sua exata callback é version-checked pelos testes"), **lido na documentação** (idempotência de score por id+nome+timestamp; cache de prompts; labels). A lista "o que ficou sem execução remota" é a mais valiosa: um turno N5 real com os três pontos instrumentados lido na UI; a sessão LF-6; o dataset `n5-baseline-v1` sincronizado; um *dataset run*; o juiz calibrado; um prompt com label `ativo` resolvido a partir do Langfuse com o turno controlado após o TTL. Cada um desses, quando executar, ganha uma linha com data — e enquanto não executar, é procedimento, não capacidade. A nota sobre `list_runs` deprecado tem paralelo: o SDK Langfuse mudou de v2 para v3/v4 com quebra de API (o plano antigo "assumia v4" e mandou confirmar); registre a versão e a data ao lado de qualquer trecho copiado.

**Em projetos comuns do ecossistema.** Para todo material técnico gerado ou co-gerado por IA, mantenha um registro de validação com: fontes primárias consultadas e data; versões do ambiente; APIs inspecionadas e o nível (executado / assinatura / docs); comandos rodados com resultado; e o que **não** foi executado. Um verificador automático (links, sintaxe, comandos locais com rede bloqueada, como o `verificar_material.py`) pega o que é mecânico. O resto é leitura.

**O fator humano — onde a IA faz e onde você decide.** Grande parte deste curso — e grande parte do pacote Langfuse da plataforma — foi escrita com assistentes (Codex, Claude). Isso torna este capítulo o mais importante do ponto de vista do fator humano, porque a IA escreve "foi executado" e "foi validado" com a mesma naturalidade com que escreve o código, e frequentemente sem que tenha sido. Você é o único capaz de **executar os passos remotos** (conta, chave, rede, custo) e, portanto, o único capaz de transformar "procedimento" em "evidência". Foque em: (1) tratar toda afirmação de execução em material gerado como pendente até você ver a saída — a revisão do Codex de 11 de setembro achou seis problemas em código já "validado", e a revisão do Claude na plataforma inverteu uma decisão de infraestrutura já "avaliada"; ambas foram leituras críticas de pessoa sobre trabalho de IA; (2) manter o registro **datado**, porque planos, preços e APIs mudam e a IA não sabe quando; (3) pedir à IA a lista do que ela **não** executou — é uma pergunta que ela responde bem quando feita, e omite quando não. A integridade de um projeto com IA não está na qualidade do código gerado; está em alguém saber, a cada momento, o que foi realmente verificado. Essa pessoa é você.
