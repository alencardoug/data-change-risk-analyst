# Contract — GraphState, Reducers, Nodes & Edges

`src/dcra/graph/state.py`, `nodes.py`, `routing.py`, `build.py`.

---

## GraphState (TypedDict)

| Field | Type | Reducer | Notes |
|---|---|---|---|
| `change_request` | ChangeRequest | last-write | set once at entry |
| `structured_change` | StructuredChange \| None | last-write | set by `interpret` |
| `evidence` | list[EvidenceItem] | **`merge_evidence`** | additive; written by the 3 collectors and by `investigate` |
| `risk` | RiskAssessment \| None | last-write | set by `assess_risk`; replaced on re-assessment |
| `risk_history` | list[RiskAssessment] | **append** | one per pass (feeds `AnalysisRecord.risk_assessments`) |
| `evidence_gap` | bool | last-write | set by `assess_risk`, cleared by `investigate` |
| `recommendations` | list[Recommendation] | **append** | every version |
| `review_actions` | list[ReviewAction] | **append** | full history |
| `revision_count` | int | last-write | incremented by routing on any RETURN |
| `status` | CaseStatus | last-write | drives the UI step view |
| `step_log` | list[str] | **append** | ordered account (FR-021) |
| `outcome` | Outcome \| None | last-write | set by `finalize` |

### Reducers
- **`merge_evidence(existing, incoming)`**: concat, drop items whose `(kind, key)` already
  present (first-write wins), return sorted by `(kind, key)`. Deterministic regardless of which
  parallel branch finishes first — this is what keeps `factors` reproducible (FR-008).
- **append**: `existing + incoming` (list concatenation) for the history lists and `step_log`.
- **last-write**: default LangGraph behavior (overwrite).

---

## Nodes

| Node | Reads | Writes | LLM? |
|---|---|---|---|
| `interpret` | `change_request` | `structured_change`, `status`, `step_log`; raises `InterpretationError` on invalid output | yes (structured) |
| `collect_asset` | `structured_change` | `evidence (+ASSET_METADATA)`, `step_log` | no |
| `collect_deps` | `structured_change` | `evidence (+DEPENDENCY)`, `step_log` | no |
| `collect_usage` | `structured_change` | `evidence (+DOWNSTREAM_USAGE)`, `step_log` | no |
| `assess_risk` | `structured_change`, `evidence` | `risk`, `risk_history`, `evidence_gap`, `status`, `step_log` | no (pure rules) |
| `investigate` | `evidence`, `risk` | `evidence (+found)`, clears `evidence_gap`, may set `risk`/`risk_history` once, `step_log` | yes (ReAct agent, read-only tools) |
| `recommend` | `structured_change`, `evidence`, `risk`, last `review_actions` note | `recommendations (+vN)`, `status`, `step_log` | yes (structured) |
| `human_review` | `risk`, last `recommendations`, `evidence` | **`interrupt(payload)`**; on resume: `review_actions (+action)`, `status`, `step_log` | no |
| `finalize` | whole state | `outcome`, `status=FINALIZED`, `step_log`; writes `AnalysisRecord` via `repository` | no |

---

## Edges

```
START ─▶ interpret
interpret ─▶ collect_asset
interpret ─▶ collect_deps
interpret ─▶ collect_usage
{collect_asset, collect_deps, collect_usage} ─▶ assess_risk        # fan-in: assess_risk runs once
assess_risk ─▶ (conditional: route_after_assess)
    evidence_gap is True         ─▶ investigate
    evidence_gap is False        ─▶ recommend
investigate ─▶ recommend
recommend ─▶ (conditional: route_after_recommend)
    risk.category == LOW         ─▶ finalize
    else                         ─▶ human_review
human_review ─▶ (conditional: route_after_review)
    decision == APPROVE | REJECT ─▶ finalize
    decision == RETURN & evidence_missing & revision_count < limit
                                 ─▶ collect_asset, collect_deps, collect_usage   # re-fan-out
    decision == RETURN & !evidence_missing & revision_count < limit
                                 ─▶ recommend
finalize ─▶ END
```

`route_after_review` increments `revision_count` on both RETURN branches before returning the
target. When `revision_count == limit`, the `human_review` interrupt payload omits the RETURN
option, so this router only ever sees APPROVE/REJECT thereafter (guarantees ≤ `limit + 1`
entries to `human_review`, SC-008).

---

## Compilation (`build.py`)

- `StateGraph(GraphState)` with the nodes/edges above.
- `checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)` (`.setup()` once at startup).
- `graph = builder.compile(checkpointer=checkpointer)`.
- No static `interrupt_before`/`interrupt_after` — the pause is the dynamic `interrupt()` inside
  `human_review`.
- Every run is invoked with `config={"configurable": {"thread_id": change_request.id},
  "recursion_limit": 40}`.

---

## Interrupt payload (what the UI renders at the gate)

```
{
  "risk": { "category": "...", "factors": [ { "code", "description", "severity" } ] },
  "recommendation": { "version", "disposition", "rationale", "mitigations", "confidence",
                      "ai_generated": true },
  "evidence": [ { "kind", "key", "status", "source", "payload" } ],
  "revision_count": int,
  "revisions_remaining": int,          # when 0 → UI shows only Approve / Reject
  "options": ["APPROVE", "REJECT", ("RETURN" if revisions_remaining > 0)]
}
```

Resume value: `Command(resume=ReviewAction(decision=..., note=..., evidence_missing=...,
reviewer=...))`.
