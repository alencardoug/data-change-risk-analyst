# Data Change Risk Analyst

A small, controlled **agentic workflow** that assesses the risk of a proposed change to a
structured data asset, gathers evidence, produces a non-binding recommendation, and **requires
human review** before any decision is recorded.

Built to demonstrate real, defensible uses of **LangGraph** (workflow orchestration, state,
deterministic routing, parallel fan-out + reducers, `interrupt`/`resume` with checkpointing, a
bounded loop) and **LangChain** (structured output, narrow read-only tools, a bounded
investigator agent) — not to be a production change-management platform.

The problem in one line: *small schema changes can break unknown consumers; a decision needs
evidence and a human in the loop.*

---

## What it does

```
"Remove the column customer_legacy_id from the orders table"
        │
   interpret        ← LLM structured output → StructuredChange
        │
   ┌────┴─────┬──────────┐      (parallel; results merged by a reducer)
 collect    collect    collect
  asset      deps       usage
   └────┬─────┴──────────┘
   assess_risk           ← deterministic rules in code → LOW | MEDIUM | HIGH + factors
        │
   evidence gap?  ──yes──►  investigate   ← bounded read-only ReAct agent
        │no                     │
   recommend  ◄─────────────────┘         ← LLM structured output → Recommendation (non-binding)
        │
   LOW ?  ──yes──►  finalize (AUTO_FINALIZED, no human review)
        │no
   human_review     ← interrupt(): the run pauses, state is checkpointed to Postgres
    ├─ approve / reject ──►  finalize (APPROVED / REJECTED)
    └─ return for revision
         ├─ note only         ──►  recommend again (risk unchanged)
         └─ "evidence missing" ──►  re-collect → re-assess (risk may change) → recommend
       (bounded: DCRA_REVISION_LIMIT returns, default 2)
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

## Three decisions worth defending in an interview

1. **Why LangGraph and not a single chain?** The process has a *pause* in the middle (human
   review) that must survive a restart, a *loop* (revision) with a termination guard, and
   *branches* that depend on deterministic state (risk category, evidence gap, revision count).
   A chain models none of these; a graph with a checkpointer models all of them. See
   `specs/001-data-change-risk-review/contracts/graph-state.md`.
2. **Why isn't the risk score produced by the LLM?** Risk policy must be predictable, auditable
   and testable, so it lives in `src/dcra/rules/risk.py` as pure functions — one factor per
   named predicate over the evidence. The LLM interprets the request and drafts the
   recommendation; it never sets the category or a routing decision (project constitution §IV).
   The whole rules module is unit-tested with no LLM calls.
3. **How is the human kept in control?** `human_review` calls `interrupt()`; the state is
   serialized to a Postgres checkpoint keyed by `thread_id`. Approve/reject/return is a real
   human decision recorded as its own field, distinct from the AI recommendation. LOW-risk
   changes auto-finalize (a deliberate, documented trade-off — ADR-015).

---

## Run it

```bash
cp .env.example .env          # fill ANTHROPIC_API_KEY (and LANGSMITH_API_KEY, or set LANGSMITH_TRACING=false)
docker compose up -d          # postgres:16
uv sync
uv run streamlit run src/dcra/app/streamlit_app.py
```

Try: `add index on orders(customer_id)` (LOW, auto-finalizes) ·
`drop column orders.customer_legacy_id` (MEDIUM, pauses for review) ·
`drop column orders.legacy_region` (unknown asset → HIGH).

## Tests

```bash
uv run pytest tests/unit tests/e2e     # deterministic — fake model + in-memory checkpointer, no API key, no DB
RUN_LLM_TESTS=1 uv run pytest tests/llm_integration   # a few real-model calls
DATABASE_URL=postgresql://dcra:dcra@localhost:5432/dcra uv run pytest tests/unit/test_repository.py
```

See `make help` for shortcuts.

---

## Layout

| Path | What |
|---|---|
| `src/dcra/domain/` | Pydantic contracts + enums |
| `src/dcra/evidence/` | simulated dataset + three read-only tools |
| `src/dcra/rules/risk.py` | deterministic risk policy (pure functions) |
| `src/dcra/llm/factory.py` | chat model + interpret / recommend / investigate (a DI seam) |
| `src/dcra/graph/` | state + reducers, nodes, routing, `build_graph` |
| `src/dcra/persistence/` | `PostgresSaver` checkpointer + `analysis_record` repository |
| `src/dcra/app/streamlit_app.py` | the demo UI |
| `specs/001-data-change-risk-review/` | the SDD artifacts (spec, plan, data-model, contracts, tasks) — the source of truth |
| `docs/learning-notes.md` | per-concept: what / why / simpler alternative / trade-off / where / how tested |
| `docs/observability.md` | reading a LangSmith trace for one case |

The root `*_SEED.md` / `DISCOVERY_NOTES.md` / `DECISIONS.md` files are the discovery record that
produced the spec.
