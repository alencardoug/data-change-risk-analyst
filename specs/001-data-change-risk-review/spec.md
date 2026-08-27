# Feature Specification: Data Change Risk Analyst

**Feature Branch**: `001-data-change-risk-review`

**Created**: 2026-08-27

**Status**: Draft

**Input**: Discovery seeds (`PROJECT_BRIEF.md`, `REQUIREMENTS_SEED.md`, `DISCOVERY_NOTES.md`), constitution v1.0.0, and decisions ADR-005 / ADR-008 / ADR-009 / ADR-010 / ADR-011 recorded in `DECISIONS.md`. `CICLO.md` describes the revision loop in plain language.

## Clarifications

### Session 2026-08-27

- Q: Which change operations must V0 recognize and interpret? → A: Drop column, alter column, and add index.
- Q: On a MEDIUM/HIGH change, when an evidence source is unavailable, what does the workflow do? → A: Continue to human review with the gap flagged and confidence marked reduced; the reviewer decides.
- Q: When the reviewer returns the recommendation with a note, can that change the risk category, or is risk fixed after the first assessment? → A: A revision may re-trigger risk assessment when the reviewer explicitly marks the note as "evidence missing"; a note without that mark only re-drives the recommendation.
- Q: What triggers the additional-investigation step (agent autonomy)? → A: An evidence gap — required evidence missing/unavailable and material to the recommendation. (No user preference expressed; recommended default adopted, revisitable in planning.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Explained risk assessment and recommendation for a proposed change (Priority: P1)

A person responsible for a data change (a **change submitter**, e.g. a data engineer) describes, in a short sentence, a change they want to make to a structured data asset — for example, *"Remove the column `customer_legacy_id` from the `orders` table."* The system turns that sentence into a structured description of the change, gathers structured facts about the affected asset and how it is used, rates the change's risk as LOW, MEDIUM, or HIGH with a list of the reasons behind that rating, and produces a non-binding recommendation about whether and how to proceed. Where a fact could not be obtained, the output says so plainly. A LOW-risk change is finalized automatically; a MEDIUM- or HIGH-risk change is held for human review (User Story 2).

**Why this priority**: This is the core value of the product and the smallest thing that is useful on its own — an explained, evidence-based risk read on a proposed change. Without it there is nothing to review.

**Independent Test**: Submit a one-line change request against the simulated evidence set and confirm the output contains: (a) a structured interpretation of the change, (b) exactly one risk category, (c) a human-readable list of contributing factors, (d) a non-binding recommendation, and (e) explicit markers for any evidence that was unavailable.

**Acceptance Scenarios**:

1. **Given** a change request naming an asset that exists in the evidence set, **When** the submitter runs the analysis, **Then** the system shows a structured interpretation, a single risk category with its factors, and a non-binding recommendation.
2. **Given** an evidence source that is unavailable during the run, **When** the analysis completes, **Then** the affected evidence is shown as "unavailable" and no unavailable fact is stated as known.
3. **Given** a change request whose text cannot be interpreted as a recognizable data change, **When** the submitter runs the analysis, **Then** the system asks for a clearer request and does not produce a risk rating.
4. **Given** a change the system rates LOW, **When** the analysis completes, **Then** a final record is created automatically — marked as auto-finalized without human review — containing the recommendation, the risk rating and factors, and the evidence considered.
5. **Given** a change whose affected asset is not present in the evidence source, **When** the analysis completes, **Then** the change is rated HIGH with an explicit "asset not found in evidence source" factor and the case proceeds to human review.

---

### User Story 2 - Human review gate with approve or reject (Priority: P2)

For a change rated MEDIUM or HIGH, before any final decision exists, the analysis pauses and waits for a **reviewing actor** (a data owner or change approver). The reviewer sees the AI recommendation — clearly marked as AI-produced — together with the risk rating, its factors, and the evidence considered, and records a decision to approve or reject. The paused analysis can be picked up later, including after the application has been restarted. When the reviewer decides, the system stores one traceable final record that keeps the AI recommendation and the human decision distinct.

**Why this priority**: Human review is what makes the workflow a controlled corporate process rather than an automated verdict, and it is the reason the system needs real pause/resume. It depends on US1 producing something to review.

**Independent Test**: From a MEDIUM- or HIGH-rated recommendation produced by US1, exercise both paths — approve leads to a final record marked APPROVED, reject leads to a final record marked REJECTED — and confirm that (a) the run does not proceed to a final record until the human acts, and (b) a run paused for review can be resumed after a full application restart and still reach a final record.

**Acceptance Scenarios**:

1. **Given** a completed recommendation for a MEDIUM- or HIGH-risk change, **When** the analysis reaches the review step, **Then** it enters a suspended state and produces no final record until a human decision is given.
2. **Given** a suspended analysis, **When** the reviewer approves, **Then** a single final record is stored with outcome APPROVED, the recommendation, the risk rating and factors, and the evidence considered, with the AI recommendation and the human decision shown as separate things.
3. **Given** a suspended analysis, **When** the reviewer rejects, **Then** a single final record is stored with outcome REJECTED and the same supporting content.
4. **Given** an analysis that was suspended for review, **When** the application is restarted and the same case is reopened, **Then** the case resumes with its prior context intact and can be decided.

---

### User Story 3 - Return a recommendation for revision (Priority: P3)

Instead of approving or rejecting, the reviewer can return the recommendation with a short written note — for example, *"the `billing_monthly` and `cs_lookup` views read this column nightly and are not in your list."* By default the system produces a revised recommendation that takes the note into account, keeping the current risk rating, and brings it back to the review step. If the reviewer marks the note as **"evidence missing"**, the system instead re-collects evidence and re-runs the risk assessment as well — so the risk category itself may change — before producing the new recommendation and returning to review. Either way, the return-and-revise cycle can happen only a limited number of times (default: two); once the limit is reached, the reviewer is offered only approve or reject.

**Why this priority**: It makes the review genuinely interactive and reflects how a real approval process handles an incomplete first answer. It is lower priority because approve/reject already delivers a complete, demonstrable workflow; the revision cycle is an enhancement on top of it.

**Independent Test**: From a recommendation at the review step, return it with an unmarked note and confirm a new recommendation version is produced that reflects the note with the risk rating unchanged; separately, return a note marked "evidence missing" and confirm evidence collection and risk assessment re-run (risk category may change) before the new recommendation. Repeat until the configured limit is reached and confirm the "return for revision" option is no longer offered while approve/reject still are.

**Acceptance Scenarios**:

1. **Given** a recommendation at the review step and a revision limit of two, **When** the reviewer returns it with an unmarked note, **Then** a new recommendation version is produced that addresses the note, the risk rating is unchanged, and the case returns to the review step with the revision recorded.
2. **Given** a recommendation at the review step, **When** the reviewer returns it with a note marked "evidence missing", **Then** the system re-collects evidence and re-runs the risk assessment (the risk category may change), produces a new recommendation, and returns the case to the review step with the revision recorded.
3. **Given** a case that has already been revised twice (in any combination of unmarked and "evidence missing" revisions), **When** the reviewer views the review step, **Then** only approve and reject are offered.
4. **Given** a reviewer who returns the recommendation with an empty note, **When** they submit, **Then** the system asks for specific feedback and does not consume a revision cycle.

---

### Edge Cases

- **Affected asset not found in the evidence set** — the change is rated HIGH with an explicit "asset not found in evidence source" factor and proceeds to human review; no asset details are fabricated (FR-020).
- **LOW-risk change** — finalized automatically without human review; the final record is marked as auto-finalized and still carries the recommendation, risk factors, and evidence (FR-019).
- **An evidence source is unavailable** — the analysis still completes; the missing items are marked "unavailable", the recommendation confidence is marked reduced, and (for MEDIUM/HIGH) both are surfaced to the reviewer. Approval is not automatically blocked (FR-024).
- **Structured interpretation fails validation** (the change cannot be represented in the expected structured form) — surfaced to the submitter as an error; no risk rating or recommendation is produced.
- **Change request text is ambiguous or is not a data-asset change at all** — the system asks for a clearer request rather than guessing an interpretation.
- **Additional investigation finds nothing new** — the recommendation proceeds using the evidence already gathered and states that enrichment did not change the picture.
- **Revision limit reached** — only approve or reject are offered; the "return for revision" path is withdrawn.
- **Duplicate submission of the same change** — each submission is treated as an independent case with its own final record.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a short free-text description of a proposed change to a data asset from a change submitter.
- **FR-002**: System MUST produce a structured representation of the requested change (at minimum: the operation, the target asset, and the target field where applicable). The recognized operations for V0 are exactly: **drop column**, **alter column** (type or nullability change), and **add index**. When the text cannot be interpreted as one of these operations against a named asset, the system MUST ask for a clearer request and MUST NOT produce a risk rating.
- **FR-003**: System MUST retrieve structured evidence about the affected asset, its dependencies, and its usage from a defined evidence source.
- **FR-004**: System MUST explicitly mark, in its output, every evidence item it attempted to obtain but could not, and MUST NOT present an unavailable item as known.
- **FR-005**: System MUST NOT state any dependency, usage, criticality, or history that was not obtained from the evidence source or from an investigation step.
- **FR-006**: System MUST classify the change's risk as exactly one of LOW, MEDIUM, or HIGH.
- **FR-007**: System MUST present the human-readable factors that produced the risk classification.
- **FR-008**: Risk classification MUST be reproducible — a given structured change together with a given set of evidence MUST always yield the same category and the same set of factors. (Across a case, the evidence set can change between assessment passes only via FR-025; each pass is itself reproducible.)
- **FR-009**: System MUST produce a non-binding recommendation describing whether and how to proceed with the change.
- **FR-010**: System MUST perform an additional-investigation step when, and only when, there is an evidence gap — required evidence is missing or unavailable and that gap could change the recommendation. Any such investigation MUST be limited to reading information and MUST NOT create, modify, or delete any system or data asset. When no evidence gap exists, this step MUST be skipped.
- **FR-011**: System MUST require a human review before any final record is created for a change classified MEDIUM or HIGH.
- **FR-012**: While awaiting human review, the analysis MUST be in a suspended state that can be resumed later — including after a full application restart — without loss of the case's prior context.
- **FR-013**: The reviewing actor MUST be able to approve or reject the recommendation.
- **FR-014**: The reviewing actor MUST be able to return the recommendation for revision together with a free-text note. When the note is not marked "evidence missing", the system MUST produce a revised recommendation that takes the note into account, keeping the existing risk classification, and return the case to the human review step.
- **FR-015**: The number of return-for-revision cycles MUST be limited by a configurable value (default: 2), counting both recommendation-only revisions (FR-014) and re-assessment revisions (FR-025). Once the limit is reached, the system MUST offer only approve or reject.
- **FR-016**: An empty or non-substantive revision note MUST NOT consume a revision cycle; the system MUST ask for specific feedback instead.
- **FR-017**: System MUST create exactly one final record for every analyzed change, containing the final human decision and outcome, every recommendation version produced, the risk classification and its factors, the evidence considered (including unavailable items), and the full revision history.
- **FR-018**: The final record and every reviewer-facing view MUST keep the AI-produced recommendation visually and structurally distinct from the human decision.
- **FR-019**: System MUST require human review for a change classified MEDIUM or HIGH. A change classified LOW MUST be finalized automatically — no human review — with the recommendation, the risk classification and factors, and the evidence considered all recorded, and the final record MUST be marked as auto-finalized without human review.
- **FR-020**: When the affected asset is not present in the evidence source, the system MUST classify the change as HIGH, MUST record an explicit factor stating the asset was not found in the evidence source, and MUST continue to human review. It MUST NOT fabricate any attribute, dependency, or usage for the missing asset.
- **FR-021**: System MUST provide, for each analyzed change, an ordered account of the steps it performed (interpretation, evidence collection, risk assessment, any additional investigation, recommendation, and each review outcome, or the auto-finalization for LOW-risk changes).
- **FR-022**: System MUST attribute each review decision to the reviewing actor. Identity handling is lightweight; corporate authentication is out of scope.
- **FR-023**: System MUST NOT execute, schedule, or apply the proposed change in any real or simulated target system; its output is limited to analysis and a recorded decision.
- **FR-024**: When an evidence source is unavailable during a MEDIUM- or HIGH-risk analysis, the system MUST still complete the analysis and reach the human review step, MUST mark the affected evidence items as unavailable, MUST mark the recommendation's confidence as reduced, and MUST surface both to the reviewer. Unavailable evidence MUST NOT by itself block approval.
- **FR-025**: The reviewing actor MUST be able to mark a return-for-revision note as "evidence missing". When so marked, the system MUST re-run evidence collection, risk assessment (which MAY change the risk category and factors), and recommendation for the case, then return it to the human review step. Each such re-assessment counts against the FR-015 revision limit.

### Key Entities *(include if feature involves data)*

- **Change Request**: the submitted proposal — raw text, structured interpretation (operation, target asset, target field where applicable), submitting actor, submission time.
- **Data Asset**: the asset affected by the change — its identifier (e.g. table and column) and the asset-level attributes relevant to risk.
- **Evidence Item**: a single fact gathered about the asset, its dependencies, or its usage — with its source and an availability status of *obtained* or *unavailable*.
- **Risk Assessment**: the outcome of rating the change — one category (LOW / MEDIUM / HIGH) and the list of contributing factors.
- **Recommendation**: a non-binding proposed course of action — its version number, the revision note that prompted it (if any), and a marker identifying it as AI-produced.
- **Review Decision**: a reviewer action — approve, reject, or return-for-revision — with the reviewing actor, the time, the free-text note when applicable, and, for a return-for-revision, whether the note is marked "evidence missing".
- **Analysis Record**: the single traceable record for a completed case — links the change request, the evidence considered, the risk assessment, every recommendation version, the revision history, and the final outcome; also records whether the case was human-reviewed or auto-finalized (LOW risk).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For 100% of the demo scenarios, a reviewer can explain in one sentence why the change was rated LOW, MEDIUM, or HIGH using only the factors the system presented.
- **SC-002**: At least two demo scenarios follow visibly different paths through the workflow — at minimum one LOW-risk case that is auto-finalized without human review, and one HIGH-risk case that enters human review and triggers additional investigation and/or at least one revision cycle.
- **SC-003**: In 100% of runs where an evidence item is unavailable, the output explicitly flags that gap, and in no run is an unavailable fact presented as known. Verified with a scenario in which an evidence source is deliberately disabled.
- **SC-004**: In 100% of reviewer-facing views and final records, the reader can tell which content is the AI recommendation and which is the human decision.
- **SC-005**: 100% of MEDIUM/HIGH analyses that were suspended for human review can be resumed after a full application restart with the same case context and can reach a final record.
- **SC-006**: 100% of analyzed changes produce exactly one final record that contains the risk category and factors, the evidence considered, every recommendation version, the revision history, and the final decision.
- **SC-007**: A first-time viewer can follow a single case from "change submitted" to "final decision recorded" in a demonstration of 3 minutes or less.
- **SC-008**: No case enters the human review step more than (revision limit + 1) times, counting both unmarked and "evidence missing" revisions.
- **SC-009**: When a MEDIUM/HIGH case runs with an evidence source disabled, 100% of such cases still reach the human review step, with the missing items and the reduced-confidence marker both visible to the reviewer.
- **SC-010**: When a reviewer returns a recommendation with a note marked "evidence missing", the resulting record shows a re-run of evidence collection and risk assessment for that pass; when the note is unmarked, the risk category and factors are identical to the previous pass.

## Out of Scope

- Executing, scheduling, or rolling out the proposed change in any target system.
- Real production data or connections to real corporate systems; the evidence set is fully simulated.
- Corporate authentication, authorization roles, and user management.
- A full change-management lifecycle (ticketing, calendars, approvals chains beyond the single review gate).
- Retrieval-augmented generation, embeddings, and vector search.
- Multi-agent orchestration.
- Pipeline or transformation-rule changes (V0 covers schema-level changes to a tabular asset).

## Assumptions

- **Actors**: a *change submitter* (e.g. data engineer) provides the request; a *reviewing actor* (data owner / change approver) decides. One person may perform both roles in the demo. Identity handling is lightweight, with no corporate authentication (per the project constitution).
- **Evidence set**: a small, fully simulated collection of structured records describing assets, their dependencies, and their usage. No real systems are queried.
- **Change scope for V0**: schema-level changes to a tabular asset, limited to the three recognized operations in FR-002 (drop column, alter column, add index). Pipeline and transformation-rule changes are excluded.
- **Non-binding recommendation**: for MEDIUM/HIGH changes the human decision always prevails. LOW-risk changes are auto-finalized by the system (FR-019); the recorded outcome for those is the recommendation itself, marked as auto-finalized without human review.
- **Revision note effect**: an unmarked returned note re-drives the recommendation step only and keeps the risk rating. A note marked "evidence missing" re-runs evidence collection and risk assessment as well, so the risk category may change within the case (FR-025).
- **Additional investigation**: read-only and bounded, and performed only when there is a material evidence gap — not on the basis of risk level (FR-010). The concrete stopping conditions for the investigation are a planning concern.
- **Independent cases**: each submission is its own case with its own final record, even when it duplicates an earlier change.
- **Default revision limit**: 2.
- **Deterministic policy**: the risk category and factors come from fixed rules, not from a model's free-form judgement.
