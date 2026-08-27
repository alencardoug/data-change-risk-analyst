# Learning notes

For each concept: **what it is · why it's here · the simpler alternative · the trade-off ·
where in the code · how it's tested.** ("Definition of Learned" from `LEARNING_OBJECTIVES.md`.)

---

## LangGraph — `StateGraph` and state as a contract

- **What**: a typed shared object (`GraphState`, a `TypedDict`) that every node reads and writes;
  the graph is a state machine over it.
- **Why here**: the workflow has data that must accumulate across steps and survive a pause
  (evidence, risk history, recommendation versions, revision count).
- **Simpler**: pass a plain dict between functions.
- **Trade-off**: the `TypedDict` + reducers are a little ceremony, but they make the merge rules
  explicit and the state serializable for checkpointing.
- **Where**: `src/dcra/graph/state.py`.
- **Tested**: `tests/unit/test_reducers.py`, and every e2e asserts on state fields.

## Deterministic conditional routing

- **What**: after a node, a pure function of the state picks the next node.
- **Why here**: "does the agent run?", "LOW auto-finalizes vs review?", "which revision branch?",
  "is the revision limit hit?" — all must be predictable and testable.
- **Simpler**: let the LLM decide the next step.
- **Trade-off**: less "agentic" flexibility; but the process is auditable and the routing is
  unit-tested without paying for a model call. Constitution §IV.
- **Where**: `route_after_assess`, `route_after_recommend`, `route_after_review` in
  `src/dcra/graph/nodes.py`.
- **Tested**: `tests/unit/test_routing.py`.

## Parallel fan-out + a reducer

- **What**: `interpret` fans out to `collect_asset` / `collect_deps` / `collect_usage`; they run
  in one superstep and their `evidence` writes are merged by `merge_evidence`.
- **Why here**: the three lookups are genuinely independent reads, and a custom reducer keeps the
  merged list **order-independent** (dedupe by `(kind, key)`, sorted) so risk factors are
  reproducible (FR-008).
- **Simpler**: one `collect_evidence` node doing the three reads in sequence.
- **Trade-off**: +1 reducer and its test; buys a real demonstration of fan-out/fan-in and why a
  plain `operator.add` reducer would make output nondeterministic.
- **Where**: `merge_evidence` in `state.py`; edges in `build.py`.
- **Tested**: `tests/unit/test_reducers.py::test_merge_evidence_order_independent`.

## Structured output

- **What**: `ChatAnthropic(...).with_structured_output(StructuredChange | Recommendation)`.
- **Why here**: schema-constrained parsing beats ad-hoc text parsing; invalid output is a
  defined failure (`InterpretationError`, or a safe fallback recommendation).
- **Simpler**: prompt for JSON and `json.loads`.
- **Trade-off**: provider-native structured output is a dependency on that capability; in return
  the parse either validates against the Pydantic model or fails loudly.
- **Where**: `src/dcra/llm/factory.py` (`interpret`, `draft_recommendation`).
- **Tested**: `tests/unit/test_domain_models.py` (the schemas), `tests/llm_integration/` (opt-in,
  real model).

## Bounded read-only agent

- **What**: `create_react_agent(model, [3 read-only tools])`, `recursion_limit≈8`, invoked only
  when `assess_risk` sets `evidence_gap` (rule: DROP/ALTER + a dependency/usage source
  UNAVAILABLE — `research.md` §5).
- **Why here**: the one place open-ended tool use earns its keep — filling a genuine evidence
  gap. It produces no risk or routing content.
- **Simpler**: no agent (do only one deterministic enrichment call), or no enrichment at all.
- **Trade-off**: agent variability and an extra model dependency, bounded by a fixed tool list
  and a recursion cap; buys a real, inspectable tool-calling loop.
- **Where**: `run_investigation` in `factory.py`; `investigate` node.
- **Tested**: `tests/llm_integration/test_investigator_agent.py` (opt-in); the deterministic
  tiers inject a scripted `fake_investigate`.

## `interrupt` / `resume` + checkpointing

- **What**: `human_review` calls `interrupt(payload)`; the run stops, state is checkpointed under
  `thread_id`; `Command(resume=ReviewAction(...))` continues it.
- **Why here**: human review must be a real workflow state that survives an app/DB restart
  (FR-012, SC-005), not a modal after the fact.
- **Simpler**: return the recommendation and collect approval outside the graph.
- **Trade-off**: needs a checkpointer (Postgres in prod, `MemorySaver` in tests) and a
  serializer allowlist for our value types; buys durable pause/resume and one `thread_id` per
  case.
- **Where**: `human_review` node; `build.py` (`run`, `resume`, `pending_interrupt`,
  `is_awaiting_review`); `persistence/checkpointer.py`, `persistence/serde.py`.
- **Tested**: `tests/e2e/test_us2_approve_reject.py`, `test_us2_resume_after_restart.py`.

## A bounded loop

- **What**: `human_review` → (RETURN) → `recommend` or → `reassess_gate` → re-collect →
  `assess_risk` → `investigate` → `recommend` → `human_review` again. `revision_count` is
  incremented in `human_review` and the router falls through to `finalize` past the limit; the
  UI withdraws the RETURN option at `revisions_remaining == 0`.
- **Why here**: mirrors a real "returned for revision" step, and exercises loop + guard + a
  multi-pass state.
- **Simpler**: approve/reject only; or a fixed single revision.
- **Trade-off**: an extra node (`reassess_gate`), a `force_investigation` flag, and three more
  e2e tests; buys the two-mode revision behavior from ADR-016 and a demonstrable guard (SC-008).
- **Where**: `route_after_review`, `reassess_gate` in `nodes.py`; loop edges in `build.py`.
- **Tested**: `tests/e2e/test_us3_*.py` (evidence-missing reassess, unmarked return, revision
  limit, empty note).

## Tracing (LangSmith)

- **What**: env-only (`LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`); LangChain
  / LangGraph auto-instrument. No code.
- **Why here**: to *see* the interrupt point, the agent's tool loop, tokens and latency for one
  case.
- **Simpler**: structured local logging (the `step_log` in every record already gives an ordered
  account — FR-021).
- **Trade-off**: a cloud account and inputs leaving the process (dataset is simulated,
  non-secret); buys trace-reading practice. See `docs/observability.md`.
