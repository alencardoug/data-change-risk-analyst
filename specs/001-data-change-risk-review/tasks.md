---
description: "Task list for Data Change Risk Analyst V0"
---

# Tasks: Data Change Risk Analyst

**Input**: Design documents from `specs/001-data-change-risk-review/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: INCLUDED. The spec, `TEST_STRATEGY_SEED.md`, and constitution (§IV, Workflow gates)
require deterministic tests separated from LLM tests. Unit + e2e run with a fake chat model;
`tests/llm_integration/` is opt-in via `RUN_LLM_TESTS=1`.

**Organization**: by user story (US1 P1 = MVP, US2 P2, US3 P3), after Setup + Foundational.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no incomplete dependencies)
- Paths are repo-root relative; single-project layout per `plan.md`.

---

## Phase 1: Setup (Shared Infrastructure)

> Note: T002/T003/T015 originally named `langchain-anthropic` / `ANTHROPIC_API_KEY` /
> `claude-opus-5`. ADR-019 switched the default provider to **OpenAI** (`langchain-openai`,
> `OPENAI_API_KEY`, `gpt-4o`); the DI seam made this a config-only change. The `.env.example`,
> `pyproject.toml`, `config.py` and `factory.py` in the repo reflect OpenAI.

- [X] T001 Create the `src/dcra/` package tree and `tests/{unit,llm_integration,e2e}/` per `plan.md` (empty `__init__.py` where needed)
- [X] T002 Author `pyproject.toml` with deps (`langgraph`, `langgraph-checkpoint-postgres`, `langchain-core`, `langchain-anthropic`, `pydantic>=2`, `psycopg[binary]`, `streamlit`, `langsmith`) and dev deps (`pytest`, `pytest-mock`); configure `ruff` + `pytest` sections
- [X] T003 [P] Add `.env.example` with `ANTHROPIC_API_KEY`, `DATABASE_URL`, `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LLM_MODEL`, `DCRA_REVISION_LIMIT`
- [X] T004 [P] Add `docker-compose.yml` with a `postgres:16` service (port 5432, named volume, healthcheck)
- [X] T005 [P] Add `tests/conftest.py` with fixtures: `fake_chat_model`, `in_memory_checkpointer`, `dataset` factory, `db_url` (skips DB tests when unset)

**Checkpoint**: `pytest` collects 0 tests without error; `docker compose config` valid.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ No user-story work begins until this phase is complete.**

- [X] T006 [P] Implement `src/dcra/domain/enums.py` (`Operation`, `RiskCategory`, `ReviewDecision`, `Outcome`, `CaseStatus`, `EvidenceKind`, `EvidenceStatus`) per `data-model.md`
- [X] T007 Implement `src/dcra/domain/models.py` Pydantic models (`ChangeRequest`, `StructuredChange` with cross-field validator, `EvidenceItem`, `RiskFactor`, `RiskAssessment`, `Recommendation`, `ReviewAction`, `AnalysisRecord`) per `data-model.md` (depends on T006)
- [X] T008 [P] Unit test `tests/unit/test_domain_models.py`: `StructuredChange` validator accepts/rejects per operation rules; `Recommendation` mitigation rule; required-field failures
- [X] T009 [P] Implement `src/dcra/config.py`: load settings from env (LLM provider/model default `claude-opus-5`, `DATABASE_URL`, LangSmith flags, `revision_limit` default 2)
- [X] T010 [P] Implement `src/dcra/evidence/dataset.py`: ~6–10 simulated assets with dependency + usage facts, one asset intentionally absent, `disabled_sources: set[str]` toggle
- [X] T011 Implement `src/dcra/evidence/tools.py`: `get_asset_metadata`, `get_dependencies`, `get_downstream_usage` as LangChain `@tool`, returning `EvidenceItem` lists; `UNAVAILABLE` on disabled source, `not_found` on missing asset; never raises for those cases (contract: `contracts/evidence-tools.md`) (depends on T007, T010)
- [X] T012 [P] Unit test `tests/unit/test_evidence_tools.py`: obtained payloads, `UNAVAILABLE` when source disabled, `not_found` for absent asset, determinism (same input → same ordered output)
- [X] T013 Implement `src/dcra/rules/risk.py`: pure `assess(structured_change, evidence) -> RiskAssessment`; named factor predicates (ASSET_NOT_FOUND→HIGH, referenced-by-view, inbound-FK, in-PK/unique, no-recent-read, add-index-no-contention→LOW); category = max severity; thresholds in module config (depends on T007)
- [X] T014 [P] Unit test `tests/unit/test_risk_rules.py`: one case per factor predicate; category mapping; empty-evidence behavior; `ASSET_NOT_FOUND` ⇒ HIGH; reproducibility (same inputs → identical `factors`)
- [X] T015 [P] Implement `src/dcra/llm/factory.py`: `build_chat_model(config)` via `langchain-anthropic`; `structured(model, Schema)` helper wrapping `.with_structured_output` with one re-ask and a typed failure (`InterpretationError` / recommendation fallback) per `contracts/llm-schemas.md`
- [X] T016 Implement `src/dcra/persistence/schema.sql` (`analysis_record` table: id, jsonb columns for change_request/structured_change/evidence/risk_assessments/recommendations/review_actions/step_log, reviewed bool, outcome text, final_recommendation_version int, timestamps)
- [X] T017 Implement `src/dcra/persistence/checkpointer.py`: build `PostgresSaver` from `DATABASE_URL`, expose `setup()` (idempotent) (depends on T009)
- [X] T018 Implement `src/dcra/persistence/repository.py`: `save(record: AnalysisRecord)`, `get(id) -> AnalysisRecord | None` via `psycopg` parametrized SQL; apply `schema.sql` on `setup()` (depends on T007, T016)
- [X] T019 [P] Integration test `tests/unit/test_repository.py` (DB-gated): round-trip an `AnalysisRecord`; `get` unknown id → None
- [X] T020 Implement `src/dcra/graph/state.py`: `GraphState` TypedDict + reducers `merge_evidence` (concat, dedupe `(kind,key)` first-write, sort) and append reducers for history lists / `step_log` (contract: `contracts/graph-state.md`) (depends on T007)
- [X] T021 [P] Unit test `tests/unit/test_reducers.py`: `merge_evidence` dedupe + stable order regardless of branch arrival order; append reducers accumulate
- [X] T022 [P] Implement `src/dcra/app/streamlit_app.py` shell: submit form, `st.session_state` for `thread_id`/last state, empty step-view container, "Reopen case" input (no graph wired yet)

**Checkpoint**: domain, config, tools, rules, LLM factory, persistence, state+reducers all unit-green; foundation ready.

**Learning objectives covered here**: structured output contracts (Pydantic), tool-as-narrow-capability, deterministic-vs-probabilistic boundary (rules in code), reducers.

---

## Phase 3: User Story 1 — Explained risk assessment & recommendation (Priority: P1) 🎯 MVP

**Goal**: Submit a one-line change → structured interpretation → parallel evidence → deterministic
risk (LOW/MEDIUM/HIGH + factors) → optional bounded investigation on evidence gap → non-binding
recommendation → LOW auto-finalizes into one `AnalysisRecord`; MEDIUM/HIGH stop with the
recommendation shown (review gate arrives in US2).

**Independent Test**: `pytest tests/e2e/test_us1_*.py` — S1 (LOW auto-finalize), S4 (evidence
source disabled → REDUCED confidence), S5 (unknown asset → HIGH), S7 (gibberish →
`InterpretationError`, no record). Plus Streamlit shows interpretation, evidence (incl.
unavailable), risk + factors, recommendation.

### Tests for User Story 1

- [X] T023 [P] [US1] e2e `tests/e2e/test_us1_low_autofinalize.py` (S1): fake model interprets `add index`; asserts LOW, `reviewed=False`, `outcome=AUTO_FINALIZED`, exactly one record, `step_log` ordered
- [X] T024 [P] [US1] e2e `tests/e2e/test_us1_evidence_unavailable.py` (S4): `usage` source disabled → `DOWNSTREAM_USAGE` items `UNAVAILABLE`, `evidence_gap` set, investigate runs, `Recommendation.confidence == REDUCED`
- [X] T025 [P] [US1] e2e `tests/e2e/test_us1_unknown_asset.py` (S5): absent asset → `ASSET_NOT_FOUND` factor, category HIGH, graph ends after `recommend` (US1 scope only — US2 repoints non-LOW to `human_review`; the gate-reach assertion for this case is T065)
- [X] T026 [P] [US1] e2e `tests/e2e/test_us1_interpretation_error.py` (S7): unparseable text → `InterpretationError`, no `AnalysisRecord` written
- [X] T027 [P] [US1] llm_integration `tests/llm_integration/test_interpretation.py` (opt-in): real model returns a schema-valid `StructuredChange` for 3 sample sentences

### Implementation for User Story 1

- [X] T028 [US1] Implement `interpret` node in `src/dcra/graph/nodes.py`: call `structured(model, StructuredChange)`, set state + `step_log`, raise `InterpretationError` on invalid output (depends on T015, T020)
- [X] T029 [P] [US1] Implement `collect_asset`, `collect_deps`, `collect_usage` nodes in `src/dcra/graph/nodes.py`: each calls its tool, writes `evidence` via `merge_evidence` (depends on T011, T020)
- [X] T030 [US1] Implement `assess_risk` node: call `rules.assess`, write `risk` + append `risk_history`, then set `evidence_gap = True` **iff** the operation is `DROP_COLUMN` or `ALTER_COLUMN` **and** at least one of the `DEPENDENCY` or `DOWNSTREAM_USAGE` evidence items has `status == UNAVAILABLE` (an `ADD_INDEX` or a fully-obtained evidence set never sets the gap; `ASSET_NOT_FOUND` is HIGH but not a "gap" — the agent cannot recover a missing asset). Record this rule in `research.md` §5. (depends on T013)
- [X] T031 [US1] Implement `investigate` node: `create_react_agent(model, [3 read-only tools])` with `recursion_limit≈8` + gap-focused system prompt; parse results into `EvidenceItem`s, merge, clear `evidence_gap`, optionally re-run `rules.assess` once (depends on T011, T015, T030; contract: `contracts/llm-schemas.md` §Call 3)
- [X] T032 [P] [US1] llm_integration `tests/llm_integration/test_investigator_agent.py` (opt-in): agent only calls the 3 allowed tools and terminates within the recursion cap
- [X] T033 [US1] Implement `recommend` node: `structured(model, Recommendation)` with evidence+risk+optional note; node assigns `version`, forces `confidence=REDUCED` when any evidence `UNAVAILABLE`, forces `ai_generated=True`, repairs invalid `mitigations` (depends on T015, T020)
- [X] T034 [US1] Implement `finalize` node (LOW path only for now): build `AnalysisRecord`, `repository.save`, set `outcome=AUTO_FINALIZED`, `reviewed=False`, `status=FINALIZED` (depends on T018)
- [X] T035 [US1] Implement `src/dcra/graph/routing.py` `route_after_assess` (gap→investigate else recommend) and `route_after_recommend` (LOW→finalize else END for US1) (depends on T020)
- [X] T036 [US1] Implement `src/dcra/graph/build.py`: assemble `StateGraph`, fan-out `interpret`→3 collectors→`assess_risk` fan-in, conditional edges, compile with `PostgresSaver`; expose `run(change_request)` and `resume(thread_id, value)` (depends on T017, T028–T035)
- [X] T037 [P] [US1] Unit test `tests/unit/test_routing.py`: `route_after_assess` / `route_after_recommend` return correct targets for LOW/MEDIUM/HIGH and gap/no-gap
- [X] T038 [US1] Wire Streamlit `app/streamlit_app.py` to `build.run`: render step-view (each `step_log` entry), evidence table (obtained + unavailable), risk badge + factor list, recommendation card labelled "AI-generated" (depends on T022, T036)
- [X] T039 [US1] Add `InterpretationError` handling in the UI: show "please restate the change", no record (depends on T038)

**Checkpoint**: MVP — analysis pipeline + LOW auto-finalize demoable end-to-end; S1/S4/S5/S7 green.

**Learning objectives covered here**: StateGraph + nodes/edges, conditional routing (deterministic),
parallelization fan-out/fan-in, structured output in practice, bounded read-only agent, LangSmith
traces visible for the above.

---

## Phase 4: User Story 2 — Human review gate: approve / reject (Priority: P2)

**Goal**: MEDIUM/HIGH cases pause at a `human_review` node via `interrupt()`; reviewer approves or
rejects; the run resumes (including after an app/DB restart) and writes one `AnalysisRecord` that
keeps the AI recommendation separate from the human decision.

**Independent Test**: `pytest tests/e2e/test_us2_*.py` — S2 (MEDIUM → approve → APPROVED), reject
variant (→ REJECTED), S8 (reach gate, restart, reopen by `thread_id`, decide), plus the HIGH /
reduced-confidence cases reaching the gate (T065).

### Tests for User Story 2

- [X] T040 [P] [US2] e2e `tests/e2e/test_us2_approve_reject.py` (S2): interrupt payload has risk/recommendation/evidence/options; resume APPROVE → `outcome=APPROVED`, `reviewed=True`; resume REJECT → `REJECTED`; AI vs human fields distinct in the record
- [X] T041 [P] [US2] e2e `tests/e2e/test_us2_resume_after_restart.py` (S8): run to interrupt, drop the in-process graph, rebuild from the same checkpointer + `thread_id`, resume, finalize
- [X] T042 [P] [US2] Unit test `tests/unit/test_state_transitions.py`: `CaseStatus` progression INTERPRETING→…→AWAITING_REVIEW→FINALIZED; no finalize before a review action for MEDIUM/HIGH
- [X] T065 [P] [US2] e2e `tests/e2e/test_us2_high_paths_reach_gate.py` (closes analyze finding G1 — FR-020, FR-024, SC-009): with US2 wiring in place, assert (a) **S5** unknown-asset case → category HIGH, `ASSET_NOT_FOUND` factor present **in the interrupt payload**, `human_review` reached, no `AnalysisRecord` before a decision; (b) **S4** `usage` source disabled → `human_review` reached with `recommendation.confidence == REDUCED` and the `UNAVAILABLE` evidence items visible in the payload; approval is offered (not auto-blocked)

### Implementation for User Story 2

- [X] T043 [US2] Implement `human_review` node in `src/dcra/graph/nodes.py`: build the interrupt payload (`contracts/graph-state.md` §Interrupt payload); on resume, append `ReviewAction`, set `step_log`/`status` (depends on T036)
- [X] T044 [US2] Extend `routing.py` with `route_after_review`: APPROVE/REJECT → `finalize` (depends on T043)
- [X] T045 [US2] Extend `finalize` node for APPROVED/REJECTED outcomes, `reviewed=True`, `final_recommendation_version` set from the standing recommendation (depends on T034, T043)
- [X] T046 [US2] Update `route_after_recommend` (non-LOW → `human_review` instead of END) and rewire edges in `build.py` (depends on T035, T036, T043)
- [X] T047 [US2] Streamlit review gate in `app/streamlit_app.py`: render interrupt payload, Approve / Reject buttons, reviewer name field; call `build.resume`; then show the final record with AI/human sections separated (depends on T038, T043)
- [X] T048 [US2] Streamlit "Reopen case": take a `thread_id`, resume from checkpoint, land on the gate or final record (depends on T047)

**Checkpoint**: US1 + US2 both independently testable; approve/reject + restart-safe resume green.

**Learning objectives covered here**: `interrupt`/`resume`, checkpointing + `thread_id`, human
review as a first-class state, idempotent resume.

---

## Phase 5: User Story 3 — Return for revision (Priority: P3)

**Goal**: Reviewer returns the recommendation with a note. Unmarked → `recommend` re-runs only
(risk unchanged). Marked "evidence missing" → evidence fan-out + `assess_risk` re-run (risk may
change) → `recommend`. Bounded by `DCRA_REVISION_LIMIT` (default 2), counting both modes; at the
limit the gate offers only approve/reject.

**Independent Test**: `pytest tests/e2e/test_us3_*.py` — S3 (return "evidence missing" → MEDIUM→HIGH
→ v2 → approve), S6 (two returns → RETURN option withdrawn), unmarked-return variant (risk
unchanged, new recommendation version), empty-note variant (no cycle consumed — T066).

### Tests for User Story 3

- [X] T049 [P] [US3] e2e `tests/e2e/test_us3_evidence_missing_reassess.py` (S3): RETURN + `evidence_missing=True` → re-collect + re-assess (`pass_number=2`, category may change) → `Recommendation.version=2` → APPROVE; `revision_count` incremented
- [X] T050 [P] [US3] e2e `tests/e2e/test_us3_unmarked_return.py`: RETURN + `evidence_missing=False` → only `recommend` re-runs; `risk` identical; `recommendations` has 2 versions
- [X] T051 [P] [US3] e2e `tests/e2e/test_us3_revision_limit.py` (S6): after 2 returns, interrupt payload `options` excludes RETURN; `revisions_remaining==0`; ≤ limit+1 entries to `human_review`
- [X] T052 [P] [US3] Unit test `tests/unit/test_routing.py::test_route_after_review_return`: both RETURN modes route correctly and increment `revision_count`; limit reached → no RETURN target ever seen
- [X] T066 [P] [US3] e2e `tests/e2e/test_us3_empty_note.py` (closes analyze finding G2 — FR-016): RETURN with a blank / whitespace-only note → system re-presents the review gate asking for specifics; `revision_count` **unchanged**; no new `Recommendation` version created; a subsequent substantive RETURN then works normally

### Implementation for User Story 3

- [X] T053 [US3] Extend `human_review` payload: compute `revisions_remaining`, include/exclude `RETURN` in `options`; accept `ReviewAction.note` + `evidence_missing` on resume; enforce substantive-note rule (FR-016) without consuming a cycle — a blank or whitespace-only note re-presents the gate asking for specifics and does **not** increment `revision_count` or create a recommendation version (verified by T066) (depends on T043, T009)
- [X] T054 [US3] Extend `route_after_review`: RETURN & !evidence_missing & under limit → `recommend`; RETURN & evidence_missing & under limit → the 3 collectors; increment `revision_count` in the router (depends on T044)
- [X] T055 [US3] Rewire `build.py` edges for the revision loop (review → collectors, review → recommend); confirm `recursion_limit` on invoke accommodates limit+1 review cycles (depends on T046, T054)
- [X] T056 [US3] `assess_risk` / `recommend`: honor `pass_number` increment and `prompted_by_note` on re-runs; `risk_history` gains an entry per re-assessment (depends on T030, T033)
- [X] T057 [US3] Streamlit: add "Return for revision" with a note box + "evidence missing" checkbox (hidden when `revisions_remaining==0`); show revision history (notes + recommendation versions + risk per pass) in the final record (depends on T047)

**Checkpoint**: all three stories independently functional; S2/S3/S6 + variants green.

**Learning objectives covered here**: loops in LangGraph with a termination guard, multi-pass
state, note-driven re-entry, why the guard lives in code not the prompt.

---

## Phase 6: Polish & Cross-Cutting

- [X] T058 [P] Write `README.md`: problem in <60s, architecture diagram, the compiled LangGraph graph image, a demo GIF, "3 decisions to defend" (workflow vs agent, deterministic risk, HITL via interrupt/checkpoint), local run steps
- [X] T059 [P] Write `docs/learning-notes.md`: per concept — what / why here / simpler alternative / trade-off / where in code / how tested (Definition of Learned from `LEARNING_OBJECTIVES.md`)
- [X] T060 [P] Add `docs/observability.md`: how to read a LangSmith trace for one case (interrupt point, agent tool loop, tokens)
- [ ] T061 Run `quickstart.md` S1–S8 against a **real model** once (needs `OPENAI_API_KEY` + Postgres; provider is OpenAI / `gpt-4o` per ADR-019). S1–S8 are already automated as e2e with a fake model; this is the live confirmation.
- [X] T062 [P] Hardening: `_normalise_rec` repair path tested (`tests/unit/test_recommendation_normalise.py`); disabled-source → UNAVAILABLE and agent-adds-0 already covered by `test_us1_evidence_unavailable`. Remaining: internal-exception → UNAVAILABLE wrapper in a node (deferred).
- [X] T063 [P] Add `ruff`/`pytest` CI-style Makefile targets (`make test`, `make lint`, `make e2e`, `make llm-test`); ensure `pytest tests/unit tests/e2e` runs with no API key
- [X] T064 Update `DECISIONS.md` with any implementation-time deviations; confirm ADR-011/015/016/017 still hold

---

## Dependencies & Execution Order

- **Phase 1 (Setup)** → **Phase 2 (Foundational)** → **Phase 3 (US1 / MVP)** → **Phase 4 (US2)** → **Phase 5 (US3)** → **Phase 6 (Polish)**
- US2 depends on US1's `build.py` graph (`route_after_recommend` non-LOW edge is repointed in T046).
- US3 depends on US2's `human_review` node and router.
- T065 (Phase 4) depends on T046 (non-LOW → `human_review` wiring). T066 (Phase 5) depends on T053/T054.
- Within a phase, `[P]` tasks touch different files and can run together.

### Parallel opportunities

- Setup: T003, T004, T005 together.
- Foundational: T006, T009, T010 together; then T008, T012, T014, T021 (tests) together; T015, T016, T022 together.
- US1 tests T023–T027 together; `collect_*` nodes T029 are one task (same file) but internally independent.
- US2 tests T040–T042 + T065 together. US3 tests T049–T052 + T066 together.
- Polish: T058, T059, T060, T062, T063 together.

> Note: T065 / T066 were added after `/speckit-analyze` (findings G1 / G2); they sit in Phases 4
> and 5 respectively despite the higher numbers. A1 was applied in place by tightening T030.

---

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + Phase 3 (US1).** Stop and validate: `pytest tests/unit tests/e2e`
green, Streamlit shows a full LOW case auto-finalize and a HIGH case with factors + recommendation.
Then add US2 (the review gate + resume), then US3 (the revision loop). Commit after each task or
logical group; each `[US#]` phase ends at an independently demoable checkpoint.

**Gate before `/speckit-implement`**: run `/speckit-analyze` to cross-check constitution ↔ spec ↔
plan ↔ tasks (every FR mapped to a task; every task traceable to an FR or a stated learning
objective; no component beyond the plan).

---

## Phase 7: Convergence

Appended by `/speckit-converge` (2026-08-27) after the V0 implementation. These close gaps
between the implemented code and the spec/plan; run `/speckit-implement` to complete them.

- [X] T067 [P] Add a DB-gated e2e that proves restart-safe resume with `PostgresSaver`: run a MEDIUM case to the `interrupt()`, then in a **fresh process / new connection** (not the same in-process saver) resume from the `thread_id` and finalize — per SC-005 / FR-012 (partial). Today `tests/e2e/test_us2_resume_after_restart.py` only rebuilds the graph object against one shared `MemorySaver`.
- [X] T068 Verify `PostgresRepository` round-trip against a live Postgres: run `tests/unit/test_repository.py` green, confirm `get()` reconstructs an `AnalysisRecord` from the jsonb columns, and fix any (de)serialization gap — per plan: persistence decision / T019 (partial; currently DB-gated and unrun).
- [X] T069 [P] Cover the Streamlit "Reopen a case by id" path: a test (or scripted check) that a reopened `thread_id` in `AWAITING_REVIEW` yields the review payload via `is_awaiting_review` + `review_payload` and can be resumed to a final record — per T048 / plan: streamlit reopen (partial).
- [X] T070 [P] Reconcile the investigator agent location: `run_investigation` lives in `src/dcra/llm/factory.py`, but `plan.md` Project Structure names `src/dcra/agent/investigator.py`. Either move it there (re-export from `factory` for callers) or add the consolidation to `plan.md`/ADR-018 — per plan: Project Structure (contradicts, minor).
- [X] T071 [P] Add a unit assertion that every `RiskFactor` a predicate can emit has a non-empty, sentence-form `description` (not just a stable `code`) — supports SC-001 ("a reviewer can explain the rating from the factors shown") (partial).
