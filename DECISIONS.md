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
**Status:** accepted

Confirmado no `/speckit-plan` (2026-08-27). LangGraph orquestra; agente LangChain é investigador read-only limitado, acionado só por lacuna de evidência. Ver ADR-017.

## ADR-007 — MCP pós-V0
**Status:** accepted

Confirmado no `/speckit-plan` (2026-08-27). V0 usa tools locais `@tool`; MCP entra como incremento V1 expondo uma tool de evidência via servidor local, com antes/depois visível. Ver ADR-017.

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
Consequências: +1 aresta condicional, +campo de estado, +guarda, +~3 testes (revisão aceita, 2ª revisão, limite). O alvo do loop foi decidido em `/speckit-clarify` — ver ADR-016.

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

## ADR-015 — Gate de revisão por nível de risco + ativo desconhecido
**Status:** accepted

Contexto: clarificações levantadas ao escrever a spec (`specs/001-data-change-risk-review/spec.md`, FR-019/FR-020).
Decisão:
- **FR-019** — risco LOW é finalizado automaticamente, sem revisão humana, com recomendação/fatores/evidência gravados e o registro marcado como "auto-finalizado sem revisão". MEDIUM e HIGH exigem revisão humana. Isso cria uma aresta condicional determinística `risco → finalizar | risco → revisar`.
- **FR-020** — ativo afetado ausente da fonte de evidência ⇒ risco HIGH com fator explícito "asset not found in evidence source", segue para revisão humana; nada sobre o ativo é inventado.
Alternativas consideradas: revisão obrigatória para toda mudança (mais simples, mas sem o branch de roteamento); LOW auto-finaliza só com evidência completa (mais defensável, roteamento mais complexo); ativo desconhecido → interromper / pedir cadastro (beco sem saída ou +escopo).
Consequências: a demo precisa de um caso LOW que "pula" o humano (bom para SC-002); o sistema grava registro final sozinho em parte dos casos — aceitável porque é controle determinístico sobre baixo impacto (Constituição II/V).

## ADR-016 — Resultados do /speckit-clarify (sessão 2026-08-27)
**Status:** accepted

Contexto: Gate 2, quatro perguntas de esclarecimento sobre `specs/001-data-change-risk-review/spec.md`.
Decisões:
- **Operações do V0 (FR-002)** — o sistema reconhece exatamente `drop column`, `alter column` (tipo/nullability) e `add index`. Perfis de risco distintos ⇒ demo com caminhos naturalmente diferentes; regras determinísticas testáveis.
- **Fonte de evidência indisponível (FR-024)** — em MEDIUM/HIGH, o fluxo segue até a revisão humana com a lacuna sinalizada e a confiança marcada como reduzida; não bloqueia aprovação automaticamente.
- **Loop de revisão e risco (FR-014 / FR-025)** — nota sem marcação re-dirige só a recomendação, mantendo o risco. Nota marcada como "evidence missing" re-roda coleta de evidência + avaliação de risco (a categoria pode mudar) antes de nova recomendação. Ambas contam para o limite de revisões (default 2). Substitui a premissa "só recomendar" do ADR-011.
- **Gatilho da investigação adicional (FR-010)** — roda apenas quando há lacuna de evidência material à recomendação; nunca por nível de risco. (Usuário sem preferência; default recomendado adotado, revisável no plan.)
Alternativas consideradas e rejeitadas: só `drop column` (demo fraca); texto livre de schema (interpretação/testes difíceis); bloquear quando evidência falta (beco sem saída); investigar sempre em HIGH (autonomia sem necessidade).
Consequências: `alter column` e `add index` entram no contrato de interpretação e nas regras de risco; o loop agora tem dois alvos possíveis (recomendação vs avaliação de risco), exigindo um flag "evidence missing" no estado e testes para os dois caminhos; FR-008 (reprodutibilidade) passa a valer por passo de avaliação, não por caso.

## ADR-017 — Plano de implementação do V0
**Status:** accepted

Contexto: Gate 4 (`/speckit-plan`), 4 decisões de arquitetura respondidas pelo usuário.
Decisões:
- **Hipótese A (workflow-first)** — LangGraph orquestra estado/roteamento/HITL/checkpoint; LangChain fornece chat model, structured output, tools de evidência e o agente investigador (read-only, `create_react_agent`, tool-list restrita, `recursion_limit`, acionado só quando `evidence_gap`).
- **Coleta de evidência paralela** — fan-out de `collect_asset` / `collect_deps` / `collect_usage` a partir de `interpret`, fan-in em `assess_risk`; `GraphState.evidence` com reducer `merge_evidence` (concat + dedupe por `(kind,key)` + ordenação estável) para preservar reprodutibilidade (FR-008). Ensina fan-out/fan-in + reducers.
- **MCP fora do V0** (confirma ADR-007).
- **Interface Streamlit** — app único mostrando etapas → evidências → risco+fatores → recomendação → gate de revisão → resume; README com diagrama + screenshots/GIF para quem não roda.
- **PostgreSQL desde já** (ADR-012) — `PostgresSaver` para checkpoints + tabela `analysis_record` para o registro final (repositório psycopg fino).
- **LangSmith sempre ligado** (ADR-013), via env.
- **Modelo default `claude-opus-5`** via `langchain-anthropic`, provider/modelo troc��vel em `config.py` (`claude-sonnet-5` como opção mais barata, escolha do usuário).
- **Testes em 3 camadas** — unit (regras/roteamento/reducers/estado/schema/repo, fake model), llm_integration (opt-in `RUN_LLM_TESTS=1`), e2e (grafo inteiro com fake model + checkpointer in-memory, cobrindo S1–S8 do quickstart).
Constitution Check: PASS, sem violações (Complexity Tracking vazio). Paralelização justificada por independência real + objetivo de aprendizado explícito.
Artefatos: `specs/001-data-change-risk-review/plan.md`, `research.md`, `data-model.md`, `contracts/{evidence-tools,llm-schemas,graph-state}.md`, `quickstart.md`.
Consequências: estrutura `src/dcra/` (core importável) + `app/streamlit_app.py` fino; docker-compose com postgres; `.env.example` com as chaves; próximo gate `/speckit-tasks`.

## ADR-018 — Desvios de implementação (V0 entregue)
**Status:** accepted

Contexto: `/speckit-implement` das Fases 1–6. Ajustes feitos durante a implementação, todos compatíveis com plan/spec.
Decisões:
- **Versões reais** — `uv` provisiona Python 3.13; `langchain-core` 1.x (o plan estimou 0.3, com nota de "conferir na implementação"). `langgraph` + `langgraph-checkpoint-postgres` atuais. Sem impacto de contrato.
- **Seam de DI** (`GraphDeps`) em vez de o grafo chamar `llm/factory` direto — permite testes determinísticos sem LLM nem banco (fake model + `MemorySaver`). `production_deps()` faz a fiação real.
- **`InterpretationError` propaga para fora do grafo** e é capturada em `run()` (em vez de uma aresta condicional de erro) — o map de aresta condicional do langgraph desta versão não aceita valor-lista para fan-out. Resultado idêntico: sem registro, erro exposto (FR-002).
- **Nó `reassess_gate` + flag `force_investigation`** — necessários para o modo "evidence missing" do loop (ADR-016): re-fan-out dos coletores e forçar o investigador a rodar naquele passo. Não estavam nomeados no `contracts/graph-state.md`, mas realizam o comportamento ali especificado.
- **`route_after_review` valida a `ReviewAction` em `resume()`** — nota de RETURN em branco levanta `ValidationError` antes de tocar o estado do grafo (FR-016), sem consumir ciclo.
- **Serializer de checkpoint com allowlist** (`persistence/serde.py`) — registra os value objects do domínio para o msgpack do langgraph (silencia o warning "unregistered type" e é à prova de futuro).
- **README reescrito** — de "SDD discovery starter" para README de produto; os seeds/`DISCOVERY_NOTES`/`DECISIONS` continuam como registro de discovery.
Consequência: 50 testes determinísticos verdes sem API key/DB; 2 testes de repositório DB-gated; `tests/llm_integration/` opt-in. ADR-011/015/016/017 permanecem válidos.

## Template

```text
## ADR-NNN — Título
Status: proposed | accepted | superseded
Contexto:
Decisão:
Alternativas:
Consequências:
```
