# Decisions

Somente decisões realmente confirmadas devem estar como `accepted`.

## ADR-001 — Projeto com dupla finalidade
**Status:** accepted

O projeto será otimizado simultaneamente para portfólio profissional e aprendizado de LangChain/LangGraph.

**Consequência:** complexidade que não melhorar nenhum dos dois objetivos deve ser removida.

## ADR-002 — Corporate but proportional
**Status:** accepted

A aparência corporativa virá de clareza de domínio, controle de risco, contratos, testes e rastreabilidade; não de infraestrutura excessiva.

## ADR-003 — RAG fora do objetivo
**Status:** accepted

Este projeto não será usado para aprofundar RAG, embeddings ou VectorDB.

## ADR-004 — Dados estruturados como domínio principal
**Status:** accepted

O projeto deve favorecer um caso com dados estruturados e pouco esforço de simulação.

## ADR-005 — Human-in-the-loop como estado de workflow
**Status:** accepted

Confirmado na sessão de discovery (2026-08-27). A revisão humana é um estado do grafo com `interrupt`/`resume`, não um botão pós-resposta. Ver ADR-010.

## ADR-006 — Workflow-first
**Status:** proposed

LangGraph como orquestrador e agent LangChain como investigador limitado. Validar durante plan.

## ADR-007 — MCP pós-V0
**Status:** proposed

Começar com tools locais e integrar MCP depois. Validar conforme objetivo educacional.

## ADR-008 — Data Change Risk Analyst
**Status:** accepted

Confirmado na sessão de discovery (2026-08-27). O domínio é análise de risco de mudança em ativo de dados estruturados (ex.: `DROP COLUMN` em `orders`). Continua veículo de aprendizado, não produto real de change management.

## ADR-009 — Duas personas, uma jornada
**Status:** accepted

Contexto: a demo precisa de um ator que propõe a mudança e um que a revisa/aprova.
Decisão: modelar **data engineer** (ator de entrada: descreve a mudança) e **data owner / change approver** (ator de revisão: recebe risco + recomendação, decide) como duas user stories ligadas pelo mesmo workflow. A "passagem de bastão" acontece no ponto de `interrupt`.
Alternativas: uma única persona (menor, mas perde a narrativa de aprovação).
Consequências: +1 user story na spec; a UI tem dois momentos distintos (submissão / revisão).

## ADR-010 — Risco categórico com fatores explicáveis
**Status:** accepted

Contexto: score numérico 0–100 é difícil de justificar e testar.
Decisão: a saída de risco é `LOW | MEDIUM | HIGH` **derivada de regras determinísticas em código/config**, acompanhada de uma lista de **fatores** (predicados testáveis sobre a evidência, ex.: "referenciada por N views", "sem leitura em 90 dias", "possui FK", "ativo desconhecido").
Alternativas: score 0–100; categoria + score combinados.
Consequências: bateria de testes determinísticos sem LLM; o LLM não define a categoria. Reforça Constitution §4.

## ADR-011 — Ciclo completo de revisão (loop no grafo)
**Status:** accepted

Contexto: aprender loop de LangGraph junto com interrupt/resume.
Decisão: na revisão humana há três saídas — **aprovar**, **rejeitar**, **pedir revisão**. "Pedir revisão" carrega uma nota em texto livre, o grafo retoma e roteia por **aresta condicional de volta** ao nó de recomendação, que regenera; então volta a pausar. Guarda de terminação: `revision_count` máx. 2 (configurável); atingido o limite, "pedir revisão" deixa de ser oferecida. Histórico de notas e versões acumulado em `revision_history` no estado.
Alternativas: só aprovar/rejeitar; aprovar/editar-inline/rejeitar sem regeneração.
Consequências: +1 aresta condicional, +campo de estado, +guarda, +~3 testes (revisão aceita, 2ª revisão, limite). A definir em clarify: a nota realimenta só `recomendar` ou também re-dispara `avaliar risco`/agente investigador (recomendação: só `recomendar`, salvo marcação explícita de "falta evidência").

## ADR-012 — PostgreSQL desde o incremento 1
**Status:** accepted

Contexto: o checkpoint precisa ser persistência real para a história de pausa/retomada.
Decisão: usar `PostgresSaver` do LangGraph como checkpointer desde o primeiro incremento; um serviço Postgres no `docker-compose`. Substitui a sugestão anterior de repositório in-memory/SQLite.
Alternativas: in-memory (perde durabilidade e demo de retomada); SQLite (durável, mas menos representativo e sem schema corporativo demonstrável).
Consequências: dependência de um Postgres local; schema com tabela de checkpoints + tabela `change_decision` (registro final). Permite inspecionar o estado serializado por `thread_id`.

## ADR-013 — LangSmith tracing obrigatório
**Status:** accepted

Contexto: objetivo de aprendizado de observabilidade agentic.
Decisão: tracing via LangSmith ligado em todos os runs (grafo, chamadas de LLM, chamadas de tool). Deixa de ser "opcional" nos seeds.
Alternativas: só logging estruturado local (suficiente funcionalmente, mas não ensina leitura de trace).
Consequências: env vars `LANGSMITH_API_KEY` / `LANGSMITH_TRACING`; conta na nuvem; cuidado para não enviar segredo em inputs. Vira objetivo de aprendizado explícito.

## ADR-014 — Constituição ratificada (v1.0.0)
**Status:** accepted

Contexto: Gate 0 do SDD_WORKFLOW.
Decisão: constituição gerada em `.specify/memory/constitution.md`, v1.0.0 (2026-08-27), com 6 princípios condensados de `CONSTITUTION_SEED.md` (10→6); o princípio "Specification outranks scaffold" virou a hierarquia de autoridade na seção Governance. Stack não é fixada na constituição — fica nos ADRs e no plan.
Alternativas: manter os 10 princípios do seed (redundância); constituição com stack embutida (perde poder de governar).
Consequências: emendas exigem novo ADR `accepted` + bump semântico; conformidade checada no gate `analyze`.

## Template

```text
## ADR-NNN — Título
Status: proposed | accepted | superseded
Contexto:
Decisão:
Alternativas:
Consequências:
```
