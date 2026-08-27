"""Domain enumerations. See specs/001-data-change-risk-review/data-model.md."""

from __future__ import annotations

from enum import StrEnum


class Operation(StrEnum):
    DROP_COLUMN = "DROP_COLUMN"
    ALTER_COLUMN = "ALTER_COLUMN"
    ADD_INDEX = "ADD_INDEX"


class RiskCategory(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

    @property
    def severity(self) -> int:
        return {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[self.value]


class ReviewDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    RETURN = "RETURN"


class Outcome(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_FINALIZED = "AUTO_FINALIZED"


class CaseStatus(StrEnum):
    INTERPRETING = "INTERPRETING"
    COLLECTING_EVIDENCE = "COLLECTING_EVIDENCE"
    ASSESSING_RISK = "ASSESSING_RISK"
    INVESTIGATING = "INVESTIGATING"
    RECOMMENDING = "RECOMMENDING"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    FINALIZED = "FINALIZED"


class EvidenceKind(StrEnum):
    ASSET_METADATA = "ASSET_METADATA"
    DEPENDENCY = "DEPENDENCY"
    DOWNSTREAM_USAGE = "DOWNSTREAM_USAGE"


class EvidenceStatus(StrEnum):
    OBTAINED = "OBTAINED"
    UNAVAILABLE = "UNAVAILABLE"


class Disposition(StrEnum):
    PROCEED = "PROCEED"
    PROCEED_WITH_MITIGATION = "PROCEED_WITH_MITIGATION"
    DO_NOT_PROCEED = "DO_NOT_PROCEED"


class Confidence(StrEnum):
    NORMAL = "NORMAL"
    REDUCED = "REDUCED"
