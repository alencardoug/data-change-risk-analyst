# Contract — LLM Structured Output

Two model calls use provider-native structured output via
`build_chat_model(settings).with_structured_output(<Model>)` (`ChatOpenAI` by default —
ADR-019). No other step lets the LLM produce free-form control data. The risk **category is
never produced by the LLM** (Constitution IV).

---

## Call 1 — Interpretation → `StructuredChange`

- **Input**: `ChangeRequest.raw_text` + a system prompt describing the three recognized
  operations and the target-shape rules.
- **Output schema**: `StructuredChange` (see `data-model.md`).
- **Success**: passes Pydantic + cross-field validation → stored on state; step_log += "interpreted".
- **Failure modes**:
  - Output does not validate (missing column for `DROP_COLUMN`, unknown operation, etc.) →
    raise `InterpretationError`; graph ends; **no `AnalysisRecord`** is written; UI shows
    "please restate the change" (spec edge case, FR-002).
  - Model expresses low confidence / "not a data change" → same path.
- **No retries in V0** beyond a single re-ask with the validation error appended (one attempt);
  keeps behavior predictable and cheap.

## Call 2 — Recommendation draft → `Recommendation`

- **Input**: `StructuredChange`, the full `evidence` list (including `UNAVAILABLE` items), the
  `RiskAssessment` (category + factors), and — on a revision — the reviewer `note`.
- **Output schema**: `Recommendation` (see `data-model.md`).
- **Rules enforced after generation** (not left to the model):
  - `version` is assigned by the node (`len(recommendations) + 1`).
  - `confidence` is forced to `REDUCED` if any evidence item is `UNAVAILABLE` (FR-024),
    regardless of what the model returned.
  - `ai_generated` is forced `True`.
  - `mitigations` must be non-empty when `disposition == PROCEED_WITH_MITIGATION`; if the model
    violates this, the node repairs by downgrading to `DO_NOT_PROCEED` with a logged note.
- **Failure mode**: output does not validate after one re-ask → the node emits a
  `Recommendation` with `disposition = DO_NOT_PROCEED`, `confidence = REDUCED`, and a rationale
  stating the draft could not be produced; the case still reaches human review (MEDIUM/HIGH) so
  a human always decides. LOW + this failure → still auto-finalizes but the record is flagged.

## Call 3 — Investigator agent (not `with_structured_output`)

- `create_react_agent(model, tools=[the three read-only tools])`, `recursion_limit ≈ 8`.
- System prompt: "You are given an evidence gap. Use only the provided read-only tools to fill
  it. Return what you found; do not speculate." 
- The node parses the agent's collected tool results into `EvidenceItem`s and merges them into
  state via the evidence reducer. The agent produces **no** risk or recommendation content.

---

## Model configuration

`src/dcra/llm/factory.py` → `build_chat_model(settings)`:
- default `provider = "openai"`, `model = "gpt-4o"` (`langchain-openai` / `ChatOpenAI`) — ADR-019
- overridable via `LLM_PROVIDER` / `LLM_MODEL` env: `gpt-4o-mini` (cheap), `o4-mini` (reasoning;
  `temperature` is dropped for `o*` models), or `anthropic` + `claude-opus-5` if the
  `langchain-anthropic` extra is installed
- `temperature = 0` (non-reasoning models)
- one place to swap providers, satisfying "provider LLM intercambiável" from the discovery notes
