# Implementation Plan: Data Change Risk Analyst

**Branch**: `001-data-change-risk-review` | **Date**: 2026-08-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-data-change-risk-review/spec.md`

## Summary

A submitter describes a schema change in one sentence; the system interprets it into a
structured change, collects structured evidence in parallel (asset metadata, dependencies,
downstream usage), applies **deterministic rules** to produce a `LOW/MEDIUM/HIGH` risk category
with explicit factors, optionally runs a **bounded read-only investigator agent** when there is
a material evidence gap, drafts a non-binding recommendation, and then either auto-finalizes
(LOW) or **pauses for human review** (MEDIUM/HIGH) with approve / reject / return-for-revision,
where a "evidence missing" return re-runs evidence + risk. Everything is one traceable record.

Technical approach: **LangGraph** owns the process (state, nodes, deterministic routing,
`interrupt`/`resume`, the revision loop, checkpointing to PostgreSQL). **LangChain** provides
the chat-model abstraction, structured output, the read-only evidence tools, and the
investigator agent. **Streamlit** renders the workflow and the review gate. **LangSmith** traces
every run. This is architecture hypothesis **A (workflow-first)** from `ARCHITECTURE_HYPOTHESES.md`.

## Technical Context

**Language/Version**: Python 3.12 (min 3.11)

**Primary Dependencies**:
- `langgraph`, `langgraph-checkpoint-postgres` — graph, state, `interrupt`/`resume`, `PostgresSaver`
- `langchain-core`, `langchain-anthropic` — `ChatAnthropic`, structured output, tool binding
- `langgraph.prebuilt` (`create_react_agent`) — bounded investigator agent
- `pydantic` v2 — all domain contracts and LLM structured output
- `psycopg[binary]` v3 — `analysis_record` persistence (thin repository, parametrized SQL)
- `streamlit` — UI
- `langsmith` — tracing (enabled via env)
- Dev: `pytest`, `pytest-mock`

**Storage**: PostgreSQL 16 (docker-compose service). LangGraph `PostgresSaver` for checkpoints
(`thread_id` per case); one additional table `analysis_record` for the final traceable record
(FR-017). Schema applied from `persistence/schema.sql` on startup.

**LLM**: default `claude-opus-5` via `langchain-anthropic`; provider/model swappable through
`config.py` (`LLM_PROVIDER`, `LLM_MODEL` env). `claude-sonnet-5` is a supported cheaper option
for high-volume local runs — the user's call, not a silent downgrade.

**Testing**: `pytest`, three tiers (see Testing Strategy). Deterministic tier runs with a
**fake chat model** and an in-memory checkpointer; LLM-integration tier is opt-in via
`RUN_LLM_TESTS=1`.

**Target Platform**: local developer machine (Linux/macOS); `docker compose up` + `streamlit run`.

**Project Type**: single project (library core + Streamlit entrypoint). Not a backend/frontend
split.

**Performance Goals**: none quantitative. Qualitative: a full case (submit → decision) is
demonstrable in ≤3 minutes (SC-007); graph steps stream to the UI as they complete.

**Constraints**: no real DDL execution; agent tools are read-only; risk category is never set
by the LLM; deterministic routing only; small fully-simulated dataset.

**Scale/Scope**: ~6–10 simulated assets with dependencies/usage; 3 recognized operations
(drop column, alter column, add index); single feature; ~1 concurrent user (demo).

## Constitution Check

*GATE: must pass before Phase 0. Re-checked after Phase 1.*

| Principle | Assessment |
|---|---|
| I. Purpose before framework / smallest sufficient system | PASS. Every component maps to a spec requirement or a stated learning objective. Parallel evidence fan-out is justified: the three reads are genuinely independent **and** it is an explicit `LEARNING_OBJECTIVES` item (reducers/parallelization). MCP deferred to V1 (ADR-007). No RAG, no multi-agent, no microservices. |
| II. Controlled autonomy, no destructive execution | PASS. LangGraph owns routing and finalization; the agent is `create_react_agent` bound **only** to three read-only evidence tools with a recursion cap; no SQL/DDL tool; the proposed change is never applied (FR-023). |
| III. Evidence over invention | PASS. `EvidenceItem` carries `status = obtained | unavailable`; nodes and UI render unavailable items explicitly (FR-004); the recommendation prompt is given only retrieved evidence; unknown asset → HIGH with a "not found" factor, no fabricated attributes (FR-020). |
| IV. Deterministic policy in code | PASS. `rules/risk.py` is pure functions: `(structured_change, evidence) -> (category, factors)`. Routing (`routing.py`) is deterministic on state fields (`risk_category`, `revision_count`, `evidence_gap`, `review_decision`). |
| V. Human review is a first-class state | PASS. `human_review` node calls `interrupt()`; state is checkpointed to Postgres; resume via `Command(resume=...)`; the record distinguishes AI recommendation from human decision (FR-018) and marks auto-finalized LOW cases (FR-019). |
| VI. Learning visibility & portfolio proportionality | PASS. Each LangChain/LangGraph use is traced (LangSmith) and shown in the Streamlit step view; README will carry the diagram + annotated screenshots/GIF so a reviewer who does not run it still sees the workflow. `DECISIONS.md` records the rationale. |
| Scope Boundaries | PASS. Structured simulated data only; two+ demo paths (LOW auto-finalize vs HIGH investigate+revise); an evidence-source-disabled scenario (FR-024). |
| Workflow & Quality Gates | PASS. This plan is Gate 4; no code yet; `/speckit-tasks` + `/speckit-analyze` precede `/speckit-implement`. |

**Result: PASS — no violations. Complexity Tracking table not required.**

## Project Structure

### Documentation (this feature)

```text
specs/001-data-change-risk-review/
├── plan.md              # this file
├── spec.md
├── research.md          # Phase 0 — decisions & rationale
├── data-model.md        # Phase 1 — entities, validation, case lifecycle
├── contracts/           # Phase 1 — internal contracts
│   ├── evidence-tools.md    # read-only tool signatures & error behavior
│   ├── llm-schemas.md       # structured-output Pydantic contracts
│   └── graph-state.md       # GraphState fields, reducers, node/edge map
├── quickstart.md        # Phase 1 — run + validate the demo scenarios
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
src/dcra/
├── __init__.py
├── config.py                 # settings: LLM provider/model, DB URL, LangSmith, revision limit
├── domain/
│   ├── enums.py              # Operation, RiskCategory, ReviewDecision, Outcome, CaseStatus
│   └── models.py             # Pydantic: ChangeRequest, StructuredChange, EvidenceItem,
│                             #   RiskAssessment, Recommendation, ReviewAction, AnalysisRecord
├── evidence/
│   ├── dataset.py            # simulated structured data + a toggle to disable a source (FR-024)
│   └── tools.py              # get_asset_metadata / get_dependencies / get_downstream_usage
│                             #   (LangChain @tool, read-only, return EvidenceItem payloads)
├── rules/
│   └── risk.py               # deterministic (structured_change, evidence) -> (category, factors)
├── agent/
│   └── investigator.py       # create_react_agent bound to the 3 read-only tools, bounded
├── llm/
│   └── factory.py            # build_chat_model(config); structured-output helpers
├── graph/
│   ├── state.py              # GraphState TypedDict + reducers
│   ├── nodes.py              # interpret, collect_asset, collect_deps, collect_usage,
│   │                         #   assess_risk, investigate, recommend, human_review, finalize
│   ├── routing.py            # deterministic conditional-edge functions
│   └── build.py              # StateGraph wiring + PostgresSaver + interrupt config
├── persistence/
│   ├── schema.sql            # analysis_record table (checkpoint tables are managed by PostgresSaver)
│   ├── checkpointer.py       # PostgresSaver construction / setup
│   └── repository.py         # AnalysisRecord read/write (psycopg, parametrized SQL)
└── app/
    └── streamlit_app.py      # submit → live steps → evidence → risk+factors → recommendation
                              #   → review gate (approve/reject/return) → resume → final record

tests/
├── unit/                     # rules, routing, reducers, state transitions, schema validation,
│                             #   repository, tool contracts — fake model, in-memory checkpointer
├── llm_integration/          # opt-in: interpretation schema, recommendation schema, agent tool-calls
└── e2e/                      # full graph with fake model: LOW auto-finalize; MEDIUM approve;
                              #   HIGH investigate + revise; "evidence missing" re-assess;
                              #   evidence source disabled; unknown asset

docker-compose.yml            # postgres:16
pyproject.toml
.env.example                  # ANTHROPIC_API_KEY, DATABASE_URL, LANGSMITH_*, LLM_MODEL, DCRA_REVISION_LIMIT
README.md                     # problem, architecture diagram, LangGraph graph image, demo GIF, decisions
```

**Structure Decision**: single project. The core is an importable library (`src/dcra/…`) so the
deterministic pieces (rules, routing, reducers) are unit-testable without Streamlit or an LLM;
`app/streamlit_app.py` is a thin driver over `graph/build.py`. Interface = **Streamlit** (the
"facilitated and visual" option the user chose): it shows the graph advancing and the
interrupt/resume gate with the least moving parts, and the README carries a diagram + annotated
screenshots/GIF for reviewers who will not run it.

## Architecture Decisions (this plan)

Recorded in `DECISIONS.md` as ADR-017 (supersedes the "proposed" status of ADR-006/007):

1. **Workflow-first (Hypothesis A).** LangGraph orchestrates; the LangChain agent is a bounded
   read-only investigator invoked only on an evidence gap.
2. **Parallel evidence collection.** `collect_asset`, `collect_deps`, `collect_usage` fan out
   from `interpret` and fan in to `assess_risk`; `GraphState.evidence` uses an additive reducer.
3. **MCP out of V0.** Evidence tools are local `@tool` functions in V0; a V1 increment re-exposes
   one via a local MCP server with a visible before/after.
4. **Streamlit interface.** Single app; no separate frontend/API.
5. **PostgreSQL from increment 1** (ADR-012) — `PostgresSaver` checkpoints + `analysis_record`.
6. **LangSmith tracing always on** (ADR-013).
7. **Default model `claude-opus-5`**, provider/model swappable via `config.py`.

## Testing Strategy

Per `TEST_STRATEGY_SEED.md`, three separated tiers:

| Tier | Scope | LLM | Runs by default |
|---|---|---|---|
| **unit** | risk rules (all factor predicates + category mapping), routing functions, reducers, state transitions, Pydantic validation (incl. invalid structured output), repository, tool contracts (obtained + unavailable) | fake chat model | yes |
| **llm_integration** | interpretation produces valid `StructuredChange`; recommendation matches schema; investigator agent calls the expected read-only tools and stops | real model, few cases | only with `RUN_LLM_TESTS=1` |
| **e2e** | whole compiled graph with a scripted fake model: LOW→auto-finalize; MEDIUM→review→approve; HIGH→investigate→return("evidence missing")→re-assess→approve; evidence source disabled→reduced confidence reaches review; unknown asset→HIGH; revision limit reached→only approve/reject | fake chat model, in-memory checkpointer | yes |

Failure cases from the seed explicitly covered: asset not found, tool unavailable, invalid
structured output, agent finds nothing new, reject, return-for-revision, resume after restart
(e2e reopens a thread from a persisted checkpoint).

## Phase 0 — Research

See [research.md](./research.md). Resolves: LangGraph `interrupt`/`resume` + `PostgresSaver`
lifecycle; fan-out/fan-in with `Annotated` reducers; `ChatAnthropic.with_structured_output`
behavior and invalid-output handling; bounding `create_react_agent` (tool allow-list +
`recursion_limit`); LangSmith env wiring; driving an interruptible graph from Streamlit
`session_state`.

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — entities, fields, validation rules, and the case lifecycle
  state machine (statuses + transitions + the revision-count guard).
- [contracts/evidence-tools.md](./contracts/evidence-tools.md) — the three read-only tool
  signatures, their `EvidenceItem` return shape, and `unavailable` behavior.
- [contracts/llm-schemas.md](./contracts/llm-schemas.md) — `StructuredChange` and
  `Recommendation` structured-output schemas and validation-failure handling.
- [contracts/graph-state.md](./contracts/graph-state.md) — `GraphState` fields, each reducer,
  and the node/edge map with routing predicates.
- [quickstart.md](./quickstart.md) — setup and the runnable demo scenarios mapped to SC-001…010.

## Complexity Tracking

No constitution violations — table intentionally omitted.
