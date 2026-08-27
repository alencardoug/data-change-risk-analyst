# Phase 0 — Research: Data Change Risk Analyst

Each item: **Decision / Rationale / Alternatives considered**. APIs must be re-checked against
current official docs at implementation time (`REFERENCES.md`).

---

## 1. LangGraph human-in-the-loop: `interrupt` / `resume`

**Decision**: the `human_review` node calls `langgraph.types.interrupt(payload)`. The app
resumes with `graph.invoke(Command(resume=<review action>), config={"configurable":
{"thread_id": <case id>}})`. The compiled graph is created with a checkpointer so the interrupt
persists.

**Rationale**: this is the supported mechanism for pausing a run and continuing later with
human input; the pause survives process restarts because the pending state lives in the
checkpoint, satisfying FR-012 / SC-005.

**Alternatives considered**:
- `interrupt_before=["human_review"]` static interrupts — simpler but the node cannot embed a
  structured payload for the UI (recommendation, factors, evidence) as cleanly; dynamic
  `interrupt()` returns exactly the review context we want to render.
- Splitting the graph into "pre-review" and "post-review" graphs and orchestrating in the app —
  loses a single `thread_id`, single trace, and single checkpoint lineage.

---

## 2. Checkpointing with PostgreSQL

**Decision**: `langgraph.checkpoint.postgres.PostgresSaver` built from `DATABASE_URL`. Call its
one-time `.setup()` on startup to create checkpoint tables. `thread_id` = the case id
(`analysis_record.id`). The final record is written by our own `repository.py` to a separate
`analysis_record` table in the same database, in the `finalize` node.

**Rationale**: ADR-012 — real durability makes "close the app, resume tomorrow" demonstrable and
gives one honest schema to show. Keeping `analysis_record` separate from checkpoint tables keeps
the portfolio-facing data model readable and independent of LangGraph internals.

**Alternatives considered**:
- `MemorySaver` — no durability; fails SC-005 as a real demo.
- `SqliteSaver` — durable but less representative and no "corporate" schema story.
- Persisting the final record as just another checkpoint field — couples our audit record to
  LangGraph's serialization format; harder to query/show.

---

## 3. Parallel evidence collection (fan-out / fan-in) and reducers

**Decision**: from `interpret`, add edges to `collect_asset`, `collect_deps`, `collect_usage`
(no edges between them); each returns `{"evidence": [EvidenceItem, ...]}`. `GraphState.evidence`
is `Annotated[list[EvidenceItem], add_evidence]` where `add_evidence` concatenates and
de-duplicates by `(kind, key)`. All three converge on `assess_risk` (LangGraph runs `assess_risk`
once, after all three complete).

**Rationale**: the three lookups are independent reads — genuine parallelism, not a contrived
demo — and reducers are an explicit learning objective. A custom reducer (vs `operator.add`)
lets us assert deterministic ordering and dedupe, which keeps FR-008 (reproducible factors)
testable.

**Alternatives considered**:
- Single `collect_evidence` node doing the three reads sequentially — simplest, no reducer, but
  forfeits the parallel-branch / reducer learning and the "visibly different paths" richness.
- `operator.add` as the reducer — works, but ordering depends on branch completion order, which
  makes factor lists non-deterministic across runs.
- Fan-out with `Send` / map-reduce — overkill for a fixed set of three named lookups.

---

## 4. Structured output with `ChatOpenAI` (provider-swappable)

**Decision**: `build_chat_model(config).with_structured_output(StructuredChange)` for
interpretation and `...with_structured_output(Recommendation)` for the recommendation draft.
Wrap each call so a validation error (malformed / non-conforming output) is caught and mapped to
an explicit domain error rather than propagating raw.

**Rationale**: schema-constrained output is more reliable than ad-hoc parsing and is a core
learning objective; explicit handling of invalid output satisfies the "structured output
invalid" failure case in the test seed and the "interpretation fails validation" edge case.

**Alternatives considered**:
- Manual JSON prompt + `json.loads` — no schema guarantees, more parsing failure modes.
- provider tool-use "extraction" pattern by hand — `with_structured_output` already wraps this.
- `PydanticOutputParser` on a plain string response — weaker than provider-native structured
  output.

---

## 5. Bounded read-only investigator agent

**Decision**: `langgraph.prebuilt.create_react_agent(model, tools=[get_asset_metadata,
get_dependencies, get_downstream_usage])`, invoked by the `investigate` node **only** when
`state.evidence_gap` is true. Bound it with `recursion_limit` (e.g. 8) and a system prompt that
restricts it to filling the identified gap and returning findings as `EvidenceItem`s. The agent
has no write/DDL tools.

**`evidence_gap` — concrete rule** (set in `assess_risk`, closes analyze finding A1): the gap is
`True` **iff** `operation ∈ {DROP_COLUMN, ALTER_COLUMN}` **and** at least one `DEPENDENCY` or
`DOWNSTREAM_USAGE` evidence item has `status == UNAVAILABLE`. `ADD_INDEX` never sets the gap
(low blast radius); a fully-obtained evidence set never sets it; `ASSET_NOT_FOUND` is HIGH but
not a gap — a missing asset is not something a read-only agent can recover, so the case goes
straight to human review. This keeps "does the agent run?" a deterministic, testable function of
the evidence, not a model judgement.

**Rationale**: this is the one place autonomy earns its place (FR-010); constraining the tool
list and recursion keeps it safe and predictable (Constitution II) and keeps the trace legible
for the "how do you observe an agent" interview question.

**Alternatives considered**:
- Free-running agent that also decides risk or finalization — violates deterministic-policy and
  controlled-autonomy principles.
- No agent (Hypothesis B) — loses the agent/tool-calling learning objective.
- Hand-written tool loop — more code, no learning benefit over the prebuilt ReAct agent for a
  bounded read-only task.

---

## 6. The revision loop and its two targets

**Decision**: `human_review` records a `ReviewAction {decision, note, evidence_missing}`.
Routing after review:
- `approve` / `reject` → `finalize`.
- `return` with `evidence_missing = false` and `revision_count < limit` → `recommend`
  (risk unchanged); increment `revision_count`.
- `return` with `evidence_missing = true` and `revision_count < limit` → back to the evidence
  fan-out → `assess_risk` → `recommend` (risk may change); increment `revision_count`.
- `revision_count >= limit` → the UI offers only approve/reject (the `return` option is not
  presented), so routing only ever sees approve/reject.

**Rationale**: directly encodes FR-014 / FR-015 / FR-025 and ADR-016; the loop guard lives in
code (Constitution IV) and caps re-entry at `limit + 1` (SC-008).

**Alternatives considered**:
- Always re-run everything on `return` — more variance, dilutes the step distinction.
- Only recommendation re-runs, never risk — rejected in `/speckit-clarify` (user chose the
  two-mode behavior).

---

## 7. Deterministic risk rules

**Decision**: `rules/risk.py` exposes `assess(structured_change, evidence) -> RiskAssessment`.
Pure function; each factor is a named predicate over the evidence (examples: asset not found →
HIGH; column referenced by ≥1 view/materialization; column has an inbound FK; column part of a
unique/primary key; no read in the usage window; `add index` with no listed contention →
downgrades). Category = highest severity triggered; factors = the list that fired. Thresholds
in a small module-level config.

**Rationale**: predictable, auditable, unit-testable without an LLM; supports SC-001 (reviewer
can explain the rating from the factors) and FR-008.

**Alternatives considered**:
- LLM assigns the category with rules as "hints" — violates Constitution IV; non-reproducible.
- Numeric 0–100 score — rejected in `/speckit-clarify` (ADR-010).

---

## 8. LangSmith tracing

**Decision**: enable via environment — `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`,
`LANGSMITH_PROJECT=dcra`. No code changes beyond reading config; LangChain/LangGraph
auto-instrument. `.env.example` documents the vars; README explains reading a trace.

**Rationale**: ADR-013; zero-intrusion observability and a real interview talking point.

**Alternatives considered**:
- Structured local logging only — functional but does not teach trace reading.
- Manual OpenTelemetry — disproportionate for V0.

**Risk / note**: traces send inputs to LangSmith. The dataset is fully simulated and non-secret;
`.env` is git-ignored. Documented as an assumption.

---

## 9. Driving an interruptible graph from Streamlit

**Decision**: `streamlit_app.py` keeps the `thread_id` and last known state in
`st.session_state`. "Analyze" calls `graph.invoke(initial_state, config)` until it hits the
interrupt; the app renders the returned review payload. Review buttons call
`graph.invoke(Command(resume=action), config)`. A "Reopen case" field takes a `thread_id` and
resumes from the persisted checkpoint (demonstrates restart-safe resume).

**Rationale**: Streamlit's re-run-on-interaction model fits a request/response call into the
graph; `session_state` + the Postgres checkpoint together mean nothing is lost on a browser
refresh or app restart.

**Alternatives considered**:
- Streaming node-by-node with `graph.stream` into a live log — nicer visual; keep as a
  polish step, not a V0 blocker.
- Background thread / async runner — unnecessary for single-user demo scale.

---

## 10. Simulated dataset shape

**Decision**: `evidence/dataset.py` holds ~6–10 assets (table.column granularity) with:
dependencies (views/materializations/FKs referencing a column), downstream usage (named
consumers + last-read timestamps). A `disabled_sources: set[str]` toggle simulates an
unavailable evidence source (FR-024). At least one asset intentionally absent to exercise
FR-020.

**Rationale**: smallest dataset that produces LOW / MEDIUM / HIGH outcomes and all failure
paths; fully in-repo, no external systems.

**Alternatives considered**:
- SQL fixtures in Postgres — adds a schema and loading step with no learning gain for V0;
  reconsider if the agent story later needs SQL-shaped tools.
- Faker-generated data — non-deterministic; harder to write stable assertions.
