# Quickstart — Data Change Risk Analyst

Validation/run guide. No implementation code here; see `contracts/` and `data-model.md` for
shapes and `tasks.md` (after `/speckit-tasks`) for build steps.

---

## Prerequisites

- Python 3.12, `uv` or `pip`
- Docker (for PostgreSQL)
- An OpenAI API key
- (Optional) a LangSmith API key — tracing is on by default; without a key set
  `LANGSMITH_TRACING=false`

## Setup

```bash
cp .env.example .env      # fill OPENAI_API_KEY, LANGSMITH_API_KEY
docker compose up -d       # postgres:16 on localhost:5432
uv sync                    # or: pip install -e ".[dev]"
# checkpoint tables + analysis_record are created on first app start
```

`.env` keys: `OPENAI_API_KEY`, `DATABASE_URL`, `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`,
`LANGSMITH_PROJECT=dcra`, `LLM_PROVIDER` (default `openai`), `LLM_MODEL` (default `gpt-4o`),
`DCRA_REVISION_LIMIT` (default 2).

## Run

```bash
streamlit run src/dcra/app/streamlit_app.py
```

Submit a change → watch the step view advance → for MEDIUM/HIGH, act at the review gate →
inspect the final record. "Reopen case" takes a case id (`thread_id`) and resumes from the
Postgres checkpoint — including after `docker compose restart` or an app restart.

## Tests

```bash
pytest tests/unit tests/e2e            # deterministic — no API calls, fake model
RUN_LLM_TESTS=1 pytest tests/llm_integration   # few real-model calls
```

---

## Demo scenarios (map to Success Criteria)

Each scenario is also an `e2e` test with a scripted fake model.

| # | Input | Expected path | Verifies |
|---|---|---|---|
| **S1** | `add index on orders(customer_id)` — no contention in dataset | interpret → collect(∥) → assess = **LOW** → recommend → **finalize AUTO_FINALIZED**, `reviewed=False` | FR-019 auto-finalize; SC-002 (path A); SC-006 one record |
| **S2** | `drop column orders.customer_legacy_id` — referenced by 2 views, last read 8 days ago | assess = **MEDIUM** → review → **APPROVE** → finalize APPROVED | FR-011/013; SC-001 (factors explain rating); SC-004 (AI vs human distinct) |
| **S3** | `drop column orders.customer_legacy_id`, reviewer returns note *"billing_monthly + cs_lookup read it nightly"* marked **evidence missing** | review → RETURN(evidence_missing) → re-collect(∥) → **re-assess (MEDIUM→HIGH)** → recommend v2 → review → APPROVE | FR-025 / ADR-016; SC-010 (re-run shown); SC-008 (≤ limit+1) |
| **S4** | `alter column orders.status` while `usage` source is disabled | collect: `DOWNSTREAM_USAGE` items `UNAVAILABLE` → assess (evidence_gap) → investigate (agent, still can't reach usage) → recommend `confidence=REDUCED` → review reachable | FR-024; FR-010 (agent on gap); SC-003, SC-009 |
| **S5** | `drop column ghost_table.foo` — asset absent from dataset | `get_asset_metadata` → `UNAVAILABLE/not_found` → assess = **HIGH** + factor `ASSET_NOT_FOUND` → review | FR-020 |
| **S6** | S2 then reviewer returns twice (any mode) | after 2nd RETURN, review gate offers only APPROVE/REJECT | FR-015; SC-008 |
| **S7** | Gibberish input (`"make the thing better"`) | `interpret` → `InterpretationError`; no record written; UI asks to restate | FR-002 edge case |
| **S8** | Run S2 to the review gate, `docker compose restart`, reopen the case id | graph resumes at `AWAITING_REVIEW` with identical payload; decision finalizes | FR-012; SC-005 |

## Constitution re-check (post-design)

Re-evaluated after Phase 1 — still **PASS**:
- Parallel fan-out has a deterministic reducer (`merge_evidence`) → FR-008 stays testable.
- Agent is read-only, tool-list-restricted, recursion-capped, gap-triggered only.
- LLM never sets risk category or routing.
- One `AnalysisRecord` per case; AI recommendation vs human decision are separate fields.
- No new components introduced during design; MCP still deferred to V1.
