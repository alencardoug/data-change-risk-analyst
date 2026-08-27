"""Checkpoint serializer with our domain types on the msgpack allowlist.

LangGraph's default serializer is permissive but warns on unregistered types and will block
them in a future release. We allow exactly our own value objects.
"""

from __future__ import annotations

from functools import lru_cache

from dcra.domain import enums, models

_ALLOWED = [
    (models.__name__, c)
    for c in (
        "ChangeRequest", "StructuredChange", "EvidenceItem", "RiskFactor", "RiskAssessment",
        "Recommendation", "ReviewAction", "AnalysisRecord",
    )
] + [
    (enums.__name__, c)
    for c in (
        "Operation", "RiskCategory", "ReviewDecision", "Outcome", "CaseStatus",
        "EvidenceKind", "EvidenceStatus", "Disposition", "Confidence",
    )
]


@lru_cache(maxsize=1)
def dcra_serde():
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    return JsonPlusSerializer(allowed_msgpack_modules=_ALLOWED)
