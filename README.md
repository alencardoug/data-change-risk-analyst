# Data Change Risk Analyst

Um **fluxo agêntico** pequeno e controlado que avalia o risco de uma mudança proposta em um
ativo de dados estruturado, reúne evidências, produz uma recomendação não vinculante e **exige
revisão humana** antes de registrar qualquer decisão.

Feito para demonstrar usos reais e defensáveis de **LangGraph** (orquestração de workflow,
estado, roteamento determinístico, fan-out paralelo + reducers, `interrupt`/`resume` com
checkpointing, um loop limitado) e **LangChain** (saída estruturada, ferramentas estreitas
somente-leitura, um agente investigador limitado) — não para ser uma plataforma de gestão de
mudanças em produção.

O problema em uma linha: *pequenas mudanças de schema podem quebrar consumidores desconhecidos;
uma decisão precisa de evidências e de um humano no circuito.*

---

## Status — concluído

Completo em funcionalidades, publicado e **congelado**: nenhuma mudança adicional está planejada.

- **No ar:** https://analisador-de-risco.web.app
- **Stack em produção:** Cloud Run (`us-east1`, scale-to-zero) + Neon Postgres + Firebase Hosting (redirect 301). Runbook em [`DEPLOYMENT.md`](DEPLOYMENT.md).
- **Texto de portfólio:** [`PORTFOLIO.md`](PORTFOLIO.md) · Documentos aprofundados em português em [`DOCS_EXPLICATIVOS/`](DOCS_EXPLICATIVOS/).
- **Defeitos conhecidos e não corrigidos:** [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md).

---

## O que ele faz

```
"Remove the column customer_legacy_id from the orders table"
        │
   interpret        ← saída estruturada do LLM → StructuredChange
        │
   ┌────┴─────┬──────────┐      (paralelo; resultados unidos por um reducer)
 collect    collect    collect
  asset      deps       usage
   └────┬─────┴──────────┘
   assess_risk           ← regras determinísticas em código → LOW | MEDIUM | HIGH + fatores
        │
   lacuna de evidência?  ──sim──►  investigate   ← agente ReAct somente-leitura e limitado
        │não                    │
   recommend  ◄────────────────┘          ← saída estruturada do LLM → Recommendation (não vinculante)
        │
   LOW ?  ──sim──►  finalize (AUTO_FINALIZED, sem revisão humana)
        │não
   human_review     ← interrupt(): a execução pausa, o estado vai para um checkpoint no Postgres
    ├─ aprovar / rejeitar ──►  finalize (APPROVED / REJECTED)
    └─ devolver para revisão
         ├─ apenas nota          ──►  recommend de novo (risco inalterado)
         └─ "evidência faltando" ──►  re-coleta → re-avalia (risco pode mudar) → recommend
       (limitado: DCRA_REVISION_LIMIT devoluções, padrão 2)
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

## Três decisões que dá para defender numa entrevista

1. **Por que LangGraph e não uma única chain?** O processo tem uma *pausa* no meio (revisão
   humana) que precisa sobreviver a um reinício, um *loop* (revisão) com uma trava de término e
   *ramificações* que dependem de estado determinístico (categoria de risco, lacuna de
   evidência, contagem de revisões). Uma chain não modela nenhum desses; um grafo com
   checkpointer modela todos. Veja
   `specs/001-data-change-risk-review/contracts/graph-state.md`.
2. **Por que o score de risco não é produzido pelo LLM?** A política de risco precisa ser
   previsível, auditável e testável, então ela vive em `src/dcra/rules/risk.py` como funções
   puras — um fator por predicado nomeado sobre as evidências. O LLM interpreta o pedido e
   redige a recomendação; ele nunca define a categoria nem uma decisão de roteamento
   (constituição do projeto §IV). O módulo de regras inteiro tem testes de unidade sem nenhuma
   chamada ao LLM.
3. **Como o humano é mantido no controle?** `human_review` chama `interrupt()`; o estado é
   serializado para um checkpoint no Postgres indexado por `thread_id`. Aprovar/rejeitar/devolver
   é uma decisão humana real, registrada em seu próprio campo, distinta da recomendação da IA.
   Mudanças de risco LOW se finalizam automaticamente (um trade-off deliberado e documentado —
   ADR-015).

---

## A demo de 2–3 minutos

Envie **`Remove the column customer_legacy_id from the orders table`** e acompanhe um caso de
ponta a ponta: interpretação estruturada → três leituras de evidência disparam em paralelo →
regras determinísticas classificam como **MEDIUM** com fatores nomeados → uma recomendação da IA
(rotulada como tal) → a execução **pausa** no portão de revisão → **Aprovar** → um
`analysis_record` rastreável. Esse único fluxo mostra o problema de negócio, a separação
determinístico/probabilístico, o fan-out paralelo com um reducer e o interrupt/resume — as
coisas que valem a pena comentar numa entrevista.

Casos de contraste: `add index on orders(customer_id)` (LOW → finaliza sozinho, sem portão) e
`drop column orders.legacy_region` (ativo ausente → HIGH, `ASSET_NOT_FOUND`).

## O que deliberadamente *não* foi construído

"Corporativo" aqui significa clareza, contratos, testes e rastreabilidade — não superfície de
recursos (constituição §I, §VI). Deixados de fora de propósito: autenticação / RBAC, um ciclo
completo de gestão de mudanças (tickets, calendários, cadeias de aprovação), microsserviços /
filas / streaming, RAG / embeddings / um banco vetorial, orquestração multi-agente, uma
ferramenta genérica ou de SQL arbitrário, dezenas de tabelas e métricas inventadas. O agente é
somente-leitura e tem teto de recursão; nenhum DDL é executado. Adicionar qualquer um desses
seria teatro corporativo para um V0 de portfólio.

---

## Como rodar

```bash
cp .env.example .env          # preencha OPENAI_API_KEY (e LANGSMITH_API_KEY, ou defina LANGSMITH_TRACING=false)
docker compose up -d          # postgres:16
uv sync
uv run streamlit run src/dcra/app/streamlit_app.py
```

Experimente: `add index on orders(customer_id)` (LOW, finaliza sozinho) ·
`drop column orders.customer_legacy_id` (MEDIUM, pausa para revisão) ·
`drop column orders.legacy_region` (ativo desconhecido → HIGH).

## Testes

```bash
uv run pytest tests/unit tests/e2e     # determinístico — modelo fake + checkpointer em memória, sem API key, sem DB
RUN_LLM_TESTS=1 uv run pytest tests/llm_integration   # algumas chamadas a modelo real
DATABASE_URL=postgresql://dcra:dcra@localhost:5432/dcra uv run pytest tests/unit/test_repository.py
```

Veja `make help` para atalhos.

---

## Estrutura

| Caminho | O que é |
|---|---|
| `src/dcra/domain/` | contratos Pydantic + enums |
| `src/dcra/evidence/` | dataset simulado + três ferramentas somente-leitura |
| `src/dcra/rules/risk.py` | política de risco determinística (funções puras) |
| `src/dcra/llm/factory.py` | modelo de chat + interpret / recommend / investigate (uma costura de DI) |
| `src/dcra/graph/` | estado + reducers, nós, roteamento, `build_graph` |
| `src/dcra/persistence/` | checkpointer `PostgresSaver` + repositório `analysis_record` |
| `src/dcra/app/streamlit_app.py` | a UI da demo |
| `src/dcra/mcp/` | incremento V1 (desligado por padrão): uma ferramenta de evidência via um servidor MCP local — veja `docs/mcp.md` |
| `specs/001-data-change-risk-review/` | os artefatos SDD (spec, plan, data-model, contracts, tasks) — a fonte da verdade |
| `docs/learning-notes.md` | por conceito: o quê / por quê / alternativa mais simples / trade-off / onde / como é testado |
| `docs/observability.md` | lendo um trace do LangSmith para um caso |
| `docs/mcp.md` | o incremento MCP: antes/depois, o que o MCP adiciona e o que não adiciona |

Os arquivos `*_SEED.md` / `DISCOVERY_NOTES.md` / `DECISIONS.md` na raiz são o registro de
discovery que produziu a spec.
