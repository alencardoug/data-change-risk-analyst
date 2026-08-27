<!--
Sync Impact Report
==================
Version change: (unversioned template) → 1.0.0
Ratification: initial adoption (project is in SDD discovery phase)

Principles (6, condensed from CONSTITUTION_SEED.md's 10):
  - I.   Purpose Before Framework & Smallest Sufficient System   (seed 1 + seed 8)
  - II.  Controlled Autonomy, No Destructive Execution           (seed 2 + seed 9)
  - III. Evidence Over Invention                                 (seed 3)
  - IV.  Deterministic Policy Lives in Code                      (seed 4)
  - V.   Human Review Is a First-Class Workflow State            (seed 5)
  - VI.  Learning Visibility & Portfolio Proportionality         (seed 6 + seed 7)
  seed 10 ("Specification outranks scaffold") → moved to Governance (authority hierarchy)

Added sections:
  - "Scope Boundaries" (Section 2) — from PROJECT_BRIEF.md constraints and non-goals
  - "Development Workflow & Quality Gates" (Section 3) — from SDD_WORKFLOW.md and CHECKLIST_DISCOVERY.md

Removed sections: none (template placeholders all resolved)

Deferred / follow-up TODOs: none
  RATIFICATION_DATE set to 2026-08-27 (adoption of this constitution; seed files predate it).

Stack intentionally NOT named here (kept at principle level). Concrete technology choices
(PostgreSQL, LangSmith, Streamlit, LangChain/LangGraph) live in DECISIONS.md ADRs and the
future plan, per Principle I and the Governance authority hierarchy.
-->

# Data Change Risk Analyst Constitution

## Core Principles

### I. Purpose Before Framework & Smallest Sufficient System

Every capability MUST exist first for product value or learning value. LangChain, LangGraph,
MCP, a database, an agent, a node, or any library MUST NOT be added only to lengthen the
technology list or to showcase a framework feature. When two designs satisfy the same product
and learning goals, the smaller one MUST be chosen. Any component that does not improve either
the portfolio objective or the learning objective MUST be removed.

**Rationale:** the project has two owners — a hiring reviewer and the author's own learning.
Complexity that serves neither is cost without return, and "enterprise theater" actively
weakens the portfolio signal.

### II. Controlled Autonomy, No Destructive Execution

Critical process steps and final relevant actions MUST remain under deterministic and/or human
control. The LLM MAY interpret input, investigate evidence, and produce recommendations, but
only within explicit, narrow limits. The investigator agent, if present, MUST be restricted to
read-only investigation. The application MUST NOT execute DDL against real systems and MUST NOT
expose a generic or arbitrary-SQL tool. Tools MUST have narrow, explicit contracts.

**Rationale:** a controlled corporate process is the thing being demonstrated. Uncontrolled
autonomy makes the demo less credible and introduces real-world risk the project does not need.

### III. Evidence Over Invention

The system MUST NOT present a dependency, usage, criticality, or corporate history as fact
unless it obtained that fact from the data source or from a tool. When evidence is missing or a
tool is unavailable, the system MUST say so explicitly; silent hallucination is a defect, not a
degraded mode.

**Rationale:** the product's entire value is trustworthy risk reasoning. A single invented
dependency destroys that trust and is indefensible in an interview.

### IV. Deterministic Policy Lives in Code

Risk rules that need to be predictable, auditable, and testable MUST live in code or
configuration, not hidden in a prompt. The risk category (LOW / MEDIUM / HIGH) MUST be derived
by deterministic rules; the LLM MUST NOT be the component that assigns it. Routing decisions
that are part of the process (which branch, whether to loop, whether to finalize) MUST be
deterministic unless a model-driven decision is explicitly justified.

**Rationale:** deterministic policy is what makes the system testable without paying for LLM
calls, and it is the clearest place to show the deterministic/probabilistic boundary.

### V. Human Review Is a First-Class Workflow State

Human approval MUST be modeled as an explicit state of the workflow with real pause and resume,
not as a cosmetic button placed after an LLM response. The AI recommendation and the human
decision MUST be distinguishable in the state, the interface, and the final record. Where a
revision loop exists, it MUST have an explicit termination guard.

**Rationale:** human-in-the-loop is both the corporate-process signal and the legitimate reason
to use persistence, interrupt, and resume — it must carry real weight in the design.

### VI. Learning Visibility & Portfolio Proportionality

Every important use of LangChain or LangGraph MUST have a recorded architectural justification
and MUST be demonstrable in the interface or the documentation. Each such use SHOULD map to a
learning objective and SHOULD record the simpler alternative that was rejected and the
trade-off accepted. Professional quality MUST be expressed through domain clarity, explicit
contracts, tests, failure handling, and traceability — not through service count, number of
files, or number of trivial ADRs.

**Rationale:** the repository has to answer interview questions ("why LangGraph and not a
chain?", "why isn't everything an agent?"). If a design choice cannot be explained and shown,
it does not belong in this project.

## Scope Boundaries

The V0 MUST stay small enough to build in a few days of focused work and to demonstrate in a
short (2–3 minute) walkthrough. The following are out of scope for this project:

- RAG, embeddings, and vector databases.
- Multi-agent orchestration without a demonstrable need.
- Real DDL execution, corporate authentication, and full change-management lifecycle.
- Large datasets and many simulated rules; the domain data MUST be small and fully simulable
  structured data.
- Microservices, Kubernetes, message queues, event streaming, and infrastructure irrelevant to
  the learning objectives.

The project MUST be runnable locally with simple instructions. At least two demo scenarios MUST
exercise different paths through the workflow, and at least one MUST exercise an evidence/tool
failure with explicit behavior.

## Development Workflow & Quality Gates

The project follows Spec-Driven Development. Artifacts generated by the Spec Kit flow are the
source of truth; the seed files at the repository root are context, not artifacts.

Gate order: `constitution → specify → clarify → requirements quality gate → plan → tasks →
analyze → implement → converge`.

- Implementation MUST NOT start while a high-impact ambiguity (scope, UX, risk, architecture)
  remains undecided.
- `plan` is the first gate allowed to fix technology, state model, nodes, tools, persistence,
  MCP scope, interface, and repository structure. Earlier gates describe WHAT and WHY only.
- Every important LangChain/LangGraph use MUST have an implementation task, a test or test
  criterion, and a related learning objective.
- Tests MUST separate deterministic logic (rules, routing, state transitions, schema
  validation, tool contracts) from LLM-integration tests (few, representative) and end-to-end
  demo tests.
- `analyze` MUST block implementation on: a requirement without a task, a task without a
  requirement or justification, a conflict with this constitution, an unnecessary architectural
  component, an unresolved critical ambiguity, or a security requirement without a mechanism.

## Governance

This constitution supersedes the seed files and any prior scaffold. When a seed conflicts with
an approved later decision, the seed loses.

Authority hierarchy, highest first: (1) this constitution; (2) the generated and clarified
feature specification; (3) approved plan and ADRs; (4) generated and analyzed tasks; (5) code;
(6) starter seed files.

Amendments: a change to this constitution MUST be recorded as an ADR in `DECISIONS.md` with
status `accepted` and MUST bump the version below. Versioning is semantic: MAJOR for a
backward-incompatible removal or redefinition of a principle or of the authority hierarchy,
MINOR for a new principle or a materially expanded section, PATCH for clarifications and
wording. Compliance with this constitution is checked at the `analyze` gate and at every
plan/spec review. Runtime guidance for agents lives in `AGENTS.md` and `CLAUDE.md`.

**Version**: 1.0.0 | **Ratified**: 2026-08-27 | **Last Amended**: 2026-08-27
