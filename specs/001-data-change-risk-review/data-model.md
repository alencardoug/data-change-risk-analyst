# Phase 1 — Data Model: Data Change Risk Analyst

Domain contracts are Pydantic v2 models in `src/dcra/domain/models.py`; enums in
`domain/enums.py`. This document is the source of truth for fields, validation, and the case
lifecycle. It does not contain code.

---

## Enums

- **Operation**: `DROP_COLUMN`, `ALTER_COLUMN`, `ADD_INDEX`
- **RiskCategory**: `LOW`, `MEDIUM`, `HIGH`
- **ReviewDecision**: `APPROVE`, `REJECT`, `RETURN`
- **Outcome**: `APPROVED`, `REJECTED`, `AUTO_FINALIZED`
- **CaseStatus**: `INTERPRETING`, `COLLECTING_EVIDENCE`, `ASSESSING_RISK`, `INVESTIGATING`,
  `RECOMMENDING`, `AWAITING_REVIEW`, `FINALIZED`
- **EvidenceKind**: `ASSET_METADATA`, `DEPENDENCY`, `DOWNSTREAM_USAGE`
- **EvidenceStatus**: `OBTAINED`, `UNAVAILABLE`

---

## Entities

### ChangeRequest
| Field | Type | Rules |
|---|---|---|
| `id` | str (uuid) | generated; also the graph `thread_id` |
| `raw_text` | str | non-empty; ≤ 500 chars |
| `submitted_by` | str | non-empty (lightweight identity; FR-022) |
| `submitted_at` | datetime | UTC |

### StructuredChange  *(LLM structured output — FR-002)*
| Field | Type | Rules |
|---|---|---|
| `operation` | Operation | must be one of the three; else interpretation fails |
| `target_table` | str | non-empty |
| `target_column` | str \| None | required for `DROP_COLUMN`, `ALTER_COLUMN`; optional for `ADD_INDEX` |
| `index_columns` | list[str] | non-empty **iff** `operation == ADD_INDEX` |
| `alter_detail` | str \| None | free text describing the type/nullability change; only for `ALTER_COLUMN` |
| `confidence` | float | 0–1; model's own parse confidence (informational) |

Validation: a cross-field validator enforces the operation/column/index constraints above. A
`StructuredChange` that fails validation → `InterpretationError` (surfaced to submitter, no risk
rating; spec edge case + FR-002).

### EvidenceItem  *(FR-003 / FR-004)*
| Field | Type | Rules |
|---|---|---|
| `kind` | EvidenceKind | |
| `key` | str | stable identifier within `kind` (e.g. dependency name) |
| `status` | EvidenceStatus | `UNAVAILABLE` when the source is disabled/failed |
| `payload` | dict \| None | present iff `OBTAINED`; never fabricated when `UNAVAILABLE` |
| `source` | str | logical source name (for the "which source was down" story) |

Dedup/order: `(kind, key)` is unique in `GraphState.evidence`; the reducer keeps first-write and
sorts by `(kind, key)` for reproducibility.

### RiskAssessment  *(FR-006 / FR-007 / FR-008)*
| Field | Type | Rules |
|---|---|---|
| `category` | RiskCategory | deterministic; = max severity of fired factors |
| `factors` | list[RiskFactor] | the predicates that fired; non-empty for MEDIUM/HIGH |
| `assessed_at` | datetime | |
| `pass_number` | int | 1 for the first assessment; incremented on an "evidence missing" re-assessment |

**RiskFactor**: `{ code: str, description: str, severity: RiskCategory }` — `code` is stable and
testable; `description` is the human-readable line shown to the reviewer.

### Recommendation  *(LLM structured output — FR-009)*
| Field | Type | Rules |
|---|---|---|
| `version` | int | 1, 2, 3… across the case |
| `disposition` | enum | `PROCEED`, `PROCEED_WITH_MITIGATION`, `DO_NOT_PROCEED` |
| `rationale` | str | non-empty; must reference only retrieved evidence/factors |
| `mitigations` | list[str] | may be empty; required non-empty when `PROCEED_WITH_MITIGATION` |
| `confidence` | enum | `NORMAL`, `REDUCED` (set `REDUCED` when any evidence item is `UNAVAILABLE`; FR-024) |
| `prompted_by_note` | str \| None | the revision note that produced this version, if any |
| `ai_generated` | bool | always `True` — marks AI authorship (FR-018) |

### ReviewAction  *(FR-013 / FR-014 / FR-025)*
| Field | Type | Rules |
|---|---|---|
| `decision` | ReviewDecision | |
| `note` | str \| None | required and substantive when `decision == RETURN` (FR-016) |
| `evidence_missing` | bool | only meaningful when `decision == RETURN`; drives re-assessment |
| `reviewer` | str | non-empty (FR-022) |
| `decided_at` | datetime | |

### AnalysisRecord  *(FR-017 — the one traceable record; persisted in `analysis_record`)*
| Field | Type | Notes |
|---|---|---|
| `id` | str (uuid) | = `ChangeRequest.id` = `thread_id` |
| `change_request` | ChangeRequest | |
| `structured_change` | StructuredChange \| None | None only if interpretation failed |
| `evidence` | list[EvidenceItem] | includes `UNAVAILABLE` items |
| `risk_assessments` | list[RiskAssessment] | one per pass (usually 1; >1 if re-assessed) |
| `recommendations` | list[Recommendation] | every version produced |
| `review_actions` | list[ReviewAction] | full revision history, ordered |
| `reviewed` | bool | `False` ⇒ auto-finalized LOW (FR-019) |
| `outcome` | Outcome | `AUTO_FINALIZED` / `APPROVED` / `REJECTED` |
| `final_recommendation_version` | int | which recommendation stands |
| `step_log` | list[str] | ordered account of steps performed (FR-021) |
| `created_at` / `finalized_at` | datetime | |

Invariant: exactly one `AnalysisRecord` per analyzed `ChangeRequest` (SC-006). The AI
recommendation(s) and the human `review_actions` are separate fields — never merged (FR-018).

### DcraDataset  *(simulated evidence source — not persisted)*
`assets: dict[str, AssetFacts]`, `disabled_sources: set[str]`. `AssetFacts` holds the
dependency and usage facts the three tools read. Absent key ⇒ tools return `UNAVAILABLE` /
"not found" (FR-020).

---

## Case Lifecycle (state machine)

```
            ┌────────────┐
submit ───▶ │ INTERPRETING│ ── interpretation fails ──▶ (end: InterpretationError, no record)
            └─────┬──────┘
                  ▼
        ┌──────────────────────┐   fan-out (parallel)
        │ COLLECTING_EVIDENCE  │  collect_asset ∥ collect_deps ∥ collect_usage
        └─────────┬────────────┘
                  ▼ fan-in
            ┌────────────┐
            │ASSESSING_RISK│  deterministic rules → (category, factors)
            └─────┬──────┘
                  ▼
        evidence_gap?  ── yes ──▶ ┌──────────────┐
                  │               │ INVESTIGATING │ bounded read-only agent
                  │               └──────┬───────┘
                  │◀─────────────────────┘ (adds EvidenceItems; may re-run rules once)
                  ▼ no
            ┌────────────┐
            │ RECOMMENDING│  LLM structured output → Recommendation(vN)
            └─────┬──────┘
                  ▼
        risk_category == LOW ? ── yes ──▶ finalize(outcome=AUTO_FINALIZED, reviewed=False) ─▶ FINALIZED
                  │ no
                  ▼
            ┌───────────────┐
            │ AWAITING_REVIEW│  interrupt() — checkpoint; resume with ReviewAction
            └──────┬────────┘
                   ├─ APPROVE ─────────────▶ finalize(APPROVED) ─▶ FINALIZED
                   ├─ REJECT ──────────────▶ finalize(REJECTED) ─▶ FINALIZED
                   ├─ RETURN, !evidence_missing, revisions<limit ─▶ RECOMMENDING (vN+1, risk unchanged); revisions++
                   ├─ RETURN,  evidence_missing, revisions<limit ─▶ COLLECTING_EVIDENCE → ASSESSING_RISK (pass_number++) → RECOMMENDING; revisions++
                   └─ revisions == limit ─▶ UI hides RETURN; only APPROVE/REJECT reachable
```

Guards & invariants:
- `revisions` (a.k.a. `revision_count`) starts at 0; both RETURN modes increment it; capped at
  `limit` (default 2, `DCRA_REVISION_LIMIT`). Max entries into `AWAITING_REVIEW` = `limit + 1`
  (SC-008).
- `evidence_gap` is set by `assess_risk` per the concrete rule in `research.md` §5
  (`operation ∈ {DROP_COLUMN, ALTER_COLUMN}` **and** some `DEPENDENCY`/`DOWNSTREAM_USAGE` item is
  `UNAVAILABLE`) and cleared after `INVESTIGATING`.
- `INVESTIGATING` may trigger at most one immediate re-run of the deterministic rules within the
  same pass; it does not itself loop.
- Transition to `FINALIZED` writes the `AnalysisRecord` and is terminal.
