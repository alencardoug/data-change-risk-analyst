# Data Change Risk Analyst

Um **fluxo de trabalho agêntico** pequeno e controlado que avalia o risco de uma mudança proposta
em um ativo de dados estruturado, coleta evidências, produz uma recomendação não vinculante e
**exige revisão humana** antes de qualquer decisão ser registrada.

Construído para demonstrar usos reais e defensáveis de **LangGraph** (orquestração de workflow,
estado, roteamento determinístico, fan-out paralelo + reducers, `interrupt`/`resume` com
checkpointing, um loop limitado) e **LangChain** (saída estruturada, tools de leitura restritas,
um agente investigador limitado) — não para ser uma plataforma de gestão de mudanças de produção.

O problema em uma linha: *pequenas mudanças de schema podem quebrar consumidores desconhecidos;
uma decisão precisa de evidência e de um humano no loop.*

---

## Status — concluído

Completo, publicado e **congelado**: não há novas features previstas.

- **No ar:** https://analisador-de-risco.web.app
- **Em produção:** Cloud Run (`us-east1`, escala a zero) + Postgres no Neon + Firebase Hosting (redirect 301). Runbook em `../DEPLOYMENT.md`.
- **Portfólio:** `../PORTFOLIO.md`. **Defeitos conhecidos e não corrigidos:** `../KNOWN_ISSUES.md`.
- **Capturas de tela:** `screenshots/`.

---

## O que faz

```
"Remove the column customer_legacy_id from the orders table"
        │
   interpret        ← saída estruturada do LLM → StructuredChange
        │
   ┌────┴─────┬──────────┐      (paralelo; resultados mesclados por um reducer)
 collect    collect    collect
  asset      deps       usage
   └────┬─────┴──────────┘
   assess_risk           ← regras determinísticas em código → LOW | MEDIUM | HIGH + fatores
        │
   lacuna de evidência?  ──sim──►  investigate   ← agente ReAct limitado, somente leitura
        │não                          │
   recommend  ◄─────────────────────────         ← saída estruturada do LLM → Recommendation (não vinculante)
        │
   LOW ?  ──sim──►  finalize (AUTO_FINALIZED, sem revisão humana)
        │não
   human_review     ← interrupt(): a execução pausa, o estado é salvo (checkpoint) no Postgres
    ├─ approve / reject ──►  finalize (APPROVED / REJECTED)
    └─ devolver para revisão
         ├─ apenas nota            ──►  recommend de novo (risco inalterado)
         └─ "evidência faltando"   ──►  recoletar → reavaliar (risco pode mudar) → recommend
       (limitado: DCRA_REVISION_LIMIT retornos, padrão 2)
```

```mermaid
graph TD;
	__start__([start]):::first
	interpret(interpret)
	collect_asset(collect_asset)
	collect_deps(collect_deps)
	collect_usage(collect_usage)
	assess_risk(assess_risk)
	reassess_gate(reassess_gate)
	investigate(investigate)
	recommend(recommend)
	human_review(human_review)
	finalize(finalize)
	__end__([end]):::last
	__start__ --> interpret;
	interpret --> collect_asset;
	interpret --> collect_deps;
	interpret --> collect_usage;
	collect_asset --> assess_risk;
	collect_deps --> assess_risk;
	collect_usage --> assess_risk;
	assess_risk -. gap .-> investigate;
	assess_risk -.-> recommend;
	investigate --> recommend;
	recommend -. LOW .-> finalize;
	recommend -. review .-> human_review;
	human_review -. approve/reject .-> finalize;
	human_review -. revise .-> recommend;
	human_review -. reassess .-> reassess_gate;
	reassess_gate --> collect_asset;
	reassess_gate --> collect_deps;
	reassess_gate --> collect_usage;
	finalize --> __end__;
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
```

---

## Três decisões que valem a pena defender em uma entrevista

1. **Por que LangGraph e não uma chain única?** O processo tem uma *pausa* no meio (revisão
   humana) que precisa sobreviver a um restart, um *loop* (revisão) com uma trava de término, e
   *branches* que dependem de estado determinístico (categoria de risco, lacuna de evidência,
   contagem de revisões). Uma chain não modela nada disso; um grafo com checkpointer modela tudo
   isso. Veja `specs/001-data-change-risk-review/contracts/graph-state.md`.
2. **Por que o score de risco não é produzido pelo LLM?** A política de risco precisa ser
   previsível, auditável e testável, então ela vive em `src/dcra/rules/risk.py` como funções
   puras — um fator por predicado nomeado sobre a evidência. O LLM interpreta o pedido e
   rascunha a recomendação; ele nunca define a categoria nem uma decisão de roteamento
   (constituição do projeto §IV). Todo o módulo de regras é testado com testes unitários sem
   nenhuma chamada de LLM.
3. **Como o humano é mantido no controle?** `human_review` chama `interrupt()`; o estado é
   serializado em um checkpoint do Postgres indexado por `thread_id`. Approve/reject/devolver é
   uma decisão humana real, registrada em um campo próprio, distinto da recomendação da IA.
   Mudanças de risco LOW se auto-finalizam (uma troca deliberada e documentada — ADR-015).

---

## A demo de 2–3 minutos

Envie **`Remove the column customer_legacy_id from the orders table`** e acompanhe um caso do
início ao fim: interpretação estruturada → três leituras de evidência em fan-out paralelo →
regras determinísticas classificam como **MEDIUM** com fatores nomeados → uma recomendação de IA
(rotulada como tal) → a execução **pausa** no gate de revisão → **Approve** → um
`analysis_record` rastreável. Esse único fluxo mostra o problema de negócio, a separação
determinístico/probabilístico, o fan-out paralelo com reducer, e o interrupt/resume — os pontos
que valem a pena discutir em uma entrevista.

Casos de contraste: `add index on orders(customer_id)` (LOW → auto-finaliza, sem gate) e
`drop column orders.legacy_region` (ativo ausente → HIGH, `ASSET_NOT_FOUND`).

## O que foi deliberadamente *não* construído

"Corporativo" aqui significa clareza, contratos, testes e rastreabilidade — não superfície
(constituição §I, §VI). Deixado de fora de propósito: autenticação / RBAC, um ciclo de vida
completo de gestão de mudanças (tickets, calendários, cadeias de aprovação), microsserviços /
filas / streaming, RAG / embeddings / um vector DB, orquestração multi-agente, uma tool de SQL
genérica ou arbitrária, dezenas de tabelas, e métricas inventadas. O agente é somente leitura e
tem limite de recursão; nenhum DDL é jamais executado. Adicionar qualquer um desses itens seria
teatro corporativo para um V0 de portfólio.

---

## Como rodar

```bash
cp .env.example .env          # preencha OPENAI_API_KEY (e LANGSMITH_API_KEY, ou defina LANGSMITH_TRACING=false)
docker compose up -d          # postgres:16
uv sync
uv run streamlit run src/dcra/app/streamlit_app.py
```

Experimente: `add index on orders(customer_id)` (LOW, auto-finaliza) ·
`drop column orders.customer_legacy_id` (MEDIUM, pausa para revisão) ·
`drop column orders.legacy_region` (ativo desconhecido → HIGH).

## Testes

```bash
uv run pytest tests/unit tests/e2e     # determinísticos — fake model + checkpointer em memória, sem API key, sem DB
RUN_LLM_TESTS=1 uv run pytest tests/llm_integration   # algumas chamadas a modelo real
DATABASE_URL=postgresql://dcra:dcra@localhost:5432/dcra uv run pytest tests/unit/test_repository.py
```

Veja `make help` para atalhos.

---

## Estrutura

| Caminho | O que é |
|---|---|
| `src/dcra/domain/` | contratos Pydantic + enums |
| `src/dcra/evidence/` | dataset simulado + três tools de leitura |
| `src/dcra/rules/risk.py` | política de risco determinística (funções puras) |
| `src/dcra/llm/factory.py` | chat model + interpret / recommend / investigate (um seam de DI) |
| `src/dcra/graph/` | estado + reducers, nós, roteamento, `build_graph` |
| `src/dcra/persistence/` | checkpointer `PostgresSaver` + repositório de `analysis_record` |
| `src/dcra/app/streamlit_app.py` | a UI da demo |
| `src/dcra/mcp/` | incremento V1 (desligado por padrão): uma tool de evidência via servidor MCP local — veja `docs/mcp.md` |
| `specs/001-data-change-risk-review/` | os artefatos de SDD (spec, plan, data-model, contracts, tasks) — a fonte da verdade |
| `docs/learning-notes.md` | por conceito: o quê / por quê / alternativa mais simples / trade-off / onde / como é testado |
| `docs/observability.md` | como ler um trace do LangSmith de um caso |
| `docs/mcp.md` | o incremento MCP: antes/depois, o que o MCP adiciona e o que não adiciona |

Os arquivos `*_SEED.md` / `DISCOVERY_NOTES.md` / `DECISIONS.md` na raiz são o registro de
discovery que produziu a spec.
