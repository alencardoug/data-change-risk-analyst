"""Deterministic risk policy (Constitution IV). Pure functions, no LLM.

``assess`` maps ``(StructuredChange, [EvidenceItem])`` to a ``RiskAssessment`` whose category is
the maximum severity of the factors that fired. Reproducible: same inputs -> identical output
(FR-008). ``has_evidence_gap`` is the A1 rule that decides whether the investigator agent runs.
"""

from __future__ import annotations

from dcra.domain.enums import EvidenceKind, EvidenceStatus, Operation, RiskCategory
from dcra.domain.models import EvidenceItem, RiskAssessment, RiskFactor, StructuredChange

# usage newer than this many days counts as "actively read"
_RECENT_DAYS = 60
_INDEX_CONTENTION_RPD = 100


def _asset_meta(evidence: list[EvidenceItem]) -> EvidenceItem | None:
    for e in evidence:
        if e.kind == EvidenceKind.ASSET_METADATA:
            return e
    return None


def _deps(evidence: list[EvidenceItem]) -> list[EvidenceItem]:
    return [e for e in evidence if e.kind == EvidenceKind.DEPENDENCY]


def _usage(evidence: list[EvidenceItem]) -> list[EvidenceItem]:
    return [e for e in evidence if e.kind == EvidenceKind.DOWNSTREAM_USAGE]


def _unavailable(evidence: list[EvidenceItem], kind: EvidenceKind) -> bool:
    return any(e.kind == kind and e.status == EvidenceStatus.UNAVAILABLE for e in evidence)


def asset_not_found(evidence: list[EvidenceItem]) -> bool:
    meta = _asset_meta(evidence)
    return bool(
        meta
        and meta.status == EvidenceStatus.UNAVAILABLE
        and (meta.payload or {}).get("reason") == "not_found"
    )


def has_evidence_gap(change: StructuredChange, evidence: list[EvidenceItem]) -> bool:
    """A1 rule (research.md §5). True iff DROP/ALTER and a dependency/usage source is UNAVAILABLE.

    ADD_INDEX never gaps; a missing asset is HIGH but not a gap (a read-only agent cannot
    recover it).
    """
    if change.operation not in (Operation.DROP_COLUMN, Operation.ALTER_COLUMN):
        return False
    if asset_not_found(evidence):
        return False
    return _unavailable(evidence, EvidenceKind.DEPENDENCY) or _unavailable(
        evidence, EvidenceKind.DOWNSTREAM_USAGE
    )


def _f(code: str, description: str, severity: RiskCategory) -> RiskFactor:
    return RiskFactor(code=code, description=description, severity=severity)


def assess(change: StructuredChange, evidence: list[EvidenceItem]) -> RiskAssessment:
    factors: list[RiskFactor] = []

    if asset_not_found(evidence):
        factors.append(
            _f("ASSET_NOT_FOUND", "Affected asset was not found in the evidence source.",
               RiskCategory.HIGH)
        )
        return _finish(factors)

    meta = _asset_meta(evidence)
    meta_payload = (meta.payload or {}) if meta else {}
    deps = _deps(evidence)
    usage = _usage(evidence)

    fk_deps = [d for d in deps if (d.payload or {}).get("dependent_type") == "foreign_key"]
    view_deps = [
        d for d in deps
        if (d.payload or {}).get("dependent_type") in ("view", "materialized_view")
    ]
    active_usage = [
        u for u in usage
        if ((u.payload or {}).get("reads_per_day") or 0) > 0
    ]

    if change.operation == Operation.ADD_INDEX:
        heavy = [u for u in usage if ((u.payload or {}).get("reads_per_day") or 0) >= _INDEX_CONTENTION_RPD]
        if heavy:
            factors.append(
                _f("INDEX_BUILD_CONTENTION",
                   f"Index target is heavily read ({len(heavy)} consumer(s) ≥ "
                   f"{_INDEX_CONTENTION_RPD} reads/day); online build advised.",
                   RiskCategory.MEDIUM)
            )
        else:
            factors.append(
                _f("ADD_INDEX_LOW_RISK",
                   "Adding an index with no listed heavy-read contention.", RiskCategory.LOW)
            )
        return _finish(factors)

    # DROP_COLUMN / ALTER_COLUMN
    if meta_payload.get("in_primary_key"):
        factors.append(_f("IN_PRIMARY_KEY", "Column participates in the primary key.",
                          RiskCategory.HIGH))
    if meta_payload.get("in_unique_constraint"):
        factors.append(_f("IN_UNIQUE_CONSTRAINT", "Column participates in a unique constraint.",
                          RiskCategory.HIGH))
    if fk_deps:
        factors.append(_f("INBOUND_FOREIGN_KEY",
                          f"{len(fk_deps)} foreign key(s) reference this column.",
                          RiskCategory.HIGH))
    if view_deps:
        factors.append(_f("REFERENCED_BY_VIEW",
                          f"Referenced by {len(view_deps)} view/materialization(s).",
                          RiskCategory.MEDIUM))
    if active_usage:
        factors.append(_f("ACTIVELY_READ",
                          f"{len(active_usage)} downstream consumer(s) still read this column.",
                          RiskCategory.MEDIUM))
    if _unavailable(evidence, EvidenceKind.DEPENDENCY) or _unavailable(
        evidence, EvidenceKind.DOWNSTREAM_USAGE
    ):
        factors.append(_f("EVIDENCE_UNAVAILABLE",
                          "Some dependency/usage evidence could not be obtained; risk is uncertain.",
                          RiskCategory.MEDIUM))
    if not factors:
        factors.append(_f("NO_DEPENDENTS_OR_USAGE",
                          "No dependents and no recorded downstream usage.", RiskCategory.LOW))
    return _finish(factors)


def _finish(factors: list[RiskFactor]) -> RiskAssessment:
    category = max((f.severity for f in factors), key=lambda c: c.severity, default=RiskCategory.LOW)
    return RiskAssessment(category=category, factors=factors)
