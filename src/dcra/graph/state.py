"""GraphState and reducers. Contract: contracts/graph-state.md."""

from __future__ import annotations

from typing import Annotated, TypedDict

from dcra.domain.enums import CaseStatus, Outcome
from dcra.domain.models import (
    ChangeRequest,
    EvidenceItem,
    Recommendation,
    ReviewAction,
    RiskAssessment,
    StructuredChange,
)


def merge_evidence(
    current: list[EvidenceItem] | None, update: list[EvidenceItem] | None
) -> list[EvidenceItem]:
    """Concat, dedupe by (kind, key) first-write-wins, sort for reproducibility (FR-008)."""
    out: dict[tuple[str, str], EvidenceItem] = {}
    for item in (current or []) + (update or []):
        k = (item.kind.value, item.key)
        out.setdefault(k, item)
    return [out[k] for k in sorted(out)]


def append_list(current: list | None, update: list | None) -> list:
    return (current or []) + (update or [])


class GraphState(TypedDict, total=False):
    change_request: ChangeRequest
    structured_change: StructuredChange | None
    evidence: Annotated[list[EvidenceItem], merge_evidence]
    risk: RiskAssessment | None
    risk_history: Annotated[list[RiskAssessment], append_list]
    evidence_gap: bool
    force_investigation: bool
    recommendations: Annotated[list[Recommendation], append_list]
    review_actions: Annotated[list[ReviewAction], append_list]
    revision_count: int
    status: CaseStatus
    step_log: Annotated[list[str], append_list]
    outcome: Outcome | None
    error: str | None
