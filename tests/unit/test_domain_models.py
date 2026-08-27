"""T008 — domain model validation."""

import pytest
from pydantic import ValidationError

from dcra.domain.enums import Disposition, EvidenceKind, EvidenceStatus, Operation, ReviewDecision
from dcra.domain.models import (
    EvidenceItem,
    Recommendation,
    ReviewAction,
    StructuredChange,
)


def test_drop_column_requires_column():
    with pytest.raises(ValidationError):
        StructuredChange(operation=Operation.DROP_COLUMN, target_table="orders")


def test_add_index_requires_index_columns():
    with pytest.raises(ValidationError):
        StructuredChange(operation=Operation.ADD_INDEX, target_table="orders")


def test_index_columns_rejected_for_non_index_op():
    with pytest.raises(ValidationError):
        StructuredChange(
            operation=Operation.DROP_COLUMN, target_table="orders",
            target_column="x", index_columns=["x"],
        )


def test_alter_detail_only_for_alter():
    with pytest.raises(ValidationError):
        StructuredChange(
            operation=Operation.DROP_COLUMN, target_table="orders",
            target_column="x", alter_detail="nullable",
        )


def test_valid_structured_changes():
    StructuredChange(operation=Operation.DROP_COLUMN, target_table="orders", target_column="x")
    StructuredChange(operation=Operation.ADD_INDEX, target_table="orders", index_columns=["a", "b"])


def test_recommendation_mitigation_rule():
    with pytest.raises(ValidationError):
        Recommendation(disposition=Disposition.PROCEED_WITH_MITIGATION, rationale="r")
    Recommendation(
        disposition=Disposition.PROCEED_WITH_MITIGATION, rationale="r", mitigations=["m"]
    )


def test_return_requires_note():
    with pytest.raises(ValidationError):
        ReviewAction(decision=ReviewDecision.RETURN, reviewer="a")
    with pytest.raises(ValidationError):
        ReviewAction(decision=ReviewDecision.RETURN, reviewer="a", note="   ")
    ReviewAction(decision=ReviewDecision.RETURN, reviewer="a", note="real feedback")


def test_unavailable_evidence_rejects_fact_payload():
    with pytest.raises(ValidationError):
        EvidenceItem(
            kind=EvidenceKind.DEPENDENCY, key="k", status=EvidenceStatus.UNAVAILABLE,
            source="lineage", payload={"dependent": "x"},
        )
    EvidenceItem(
        kind=EvidenceKind.ASSET_METADATA, key="k", status=EvidenceStatus.UNAVAILABLE,
        source="catalog", payload={"reason": "not_found"},
    )
