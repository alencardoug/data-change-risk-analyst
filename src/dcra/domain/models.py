"""Pydantic domain contracts. See specs/001-data-change-risk-review/data-model.md."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator

from dcra.domain.enums import (
    Confidence,
    Disposition,
    EvidenceKind,
    EvidenceStatus,
    Operation,
    Outcome,
    ReviewDecision,
    RiskCategory,
)


class DcraError(Exception):
    """Base class for expected domain failures."""


class InterpretationError(DcraError):
    """The change request could not be interpreted as a recognised data change (FR-002)."""


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class ChangeRequest(BaseModel):
    id: str = Field(default_factory=_uuid)
    raw_text: str = Field(min_length=1, max_length=500)
    submitted_by: str = Field(min_length=1)
    submitted_at: datetime = Field(default_factory=_now)


class StructuredChange(BaseModel):
    """LLM structured output for FR-002."""

    operation: Operation
    target_table: str = Field(min_length=1)
    target_column: str | None = None
    index_columns: list[str] = Field(default_factory=list)
    alter_detail: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_shape(self) -> StructuredChange:
        if self.operation in (Operation.DROP_COLUMN, Operation.ALTER_COLUMN):
            if not self.target_column:
                raise ValueError(f"{self.operation.value} requires target_column")
        if self.operation == Operation.ADD_INDEX:
            if not self.index_columns:
                raise ValueError("ADD_INDEX requires a non-empty index_columns")
        else:
            if self.index_columns:
                raise ValueError("index_columns is only valid for ADD_INDEX")
        if self.alter_detail and self.operation != Operation.ALTER_COLUMN:
            raise ValueError("alter_detail is only valid for ALTER_COLUMN")
        return self


class EvidenceItem(BaseModel):
    kind: EvidenceKind
    key: str
    status: EvidenceStatus
    source: str
    payload: dict | None = None

    @model_validator(mode="after")
    def _check_payload(self) -> EvidenceItem:
        # never fabricate facts for an unavailable item (Constitution III)
        allowed = (None, {}, {"reason": "not_found"})
        if self.status == EvidenceStatus.UNAVAILABLE and self.payload not in allowed:
            raise ValueError("UNAVAILABLE evidence must not carry a fact payload")
        return self


class RiskFactor(BaseModel):
    code: str
    description: str
    severity: RiskCategory


class RiskAssessment(BaseModel):
    category: RiskCategory
    factors: list[RiskFactor] = Field(default_factory=list)
    assessed_at: datetime = Field(default_factory=_now)
    pass_number: int = 1


class Recommendation(BaseModel):
    """LLM structured output for FR-009. Node overrides version/confidence/ai_generated."""

    version: int = 1
    disposition: Disposition
    rationale: str = Field(min_length=1)
    mitigations: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.NORMAL
    prompted_by_note: str | None = None
    ai_generated: bool = True

    @model_validator(mode="after")
    def _check_mitigations(self) -> Recommendation:
        if self.disposition == Disposition.PROCEED_WITH_MITIGATION and not self.mitigations:
            raise ValueError("PROCEED_WITH_MITIGATION requires at least one mitigation")
        return self


class ReviewAction(BaseModel):
    decision: ReviewDecision
    reviewer: str = Field(min_length=1)
    note: str | None = None
    evidence_missing: bool = False
    decided_at: datetime = Field(default_factory=_now)

    @model_validator(mode="after")
    def _check_return(self) -> ReviewAction:
        if self.decision == ReviewDecision.RETURN and not (self.note and self.note.strip()):
            raise ValueError("RETURN requires a non-empty note")
        return self


class AnalysisRecord(BaseModel):
    """The one traceable record per analysed change (FR-017)."""

    id: str
    change_request: ChangeRequest
    structured_change: StructuredChange | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    risk_assessments: list[RiskAssessment] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    review_actions: list[ReviewAction] = Field(default_factory=list)
    reviewed: bool = False
    outcome: Outcome
    final_recommendation_version: int
    step_log: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    finalized_at: datetime = Field(default_factory=_now)
