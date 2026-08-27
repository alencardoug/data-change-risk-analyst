"""T014 — deterministic risk rules."""

from dcra.domain.enums import EvidenceKind, EvidenceStatus, Operation, RiskCategory
from dcra.domain.models import EvidenceItem, StructuredChange
from dcra.rules.risk import assess, has_evidence_gap


def _meta(**payload) -> EvidenceItem:
    return EvidenceItem(kind=EvidenceKind.ASSET_METADATA, key="orders.x",
                        status=EvidenceStatus.OBTAINED, source="catalog", payload=payload)


def _dep(dep_type: str) -> EvidenceItem:
    return EvidenceItem(kind=EvidenceKind.DEPENDENCY, key=f"d-{dep_type}",
                        status=EvidenceStatus.OBTAINED, source="lineage",
                        payload={"dependent_type": dep_type})


def _usage(rpd: int) -> EvidenceItem:
    return EvidenceItem(kind=EvidenceKind.DOWNSTREAM_USAGE, key="c",
                        status=EvidenceStatus.OBTAINED, source="usage",
                        payload={"reads_per_day": rpd})


def _unavail(kind: EvidenceKind) -> EvidenceItem:
    src = {EvidenceKind.DEPENDENCY: "lineage", EvidenceKind.DOWNSTREAM_USAGE: "usage",
           EvidenceKind.ASSET_METADATA: "catalog"}[kind]
    return EvidenceItem(kind=kind, key="k", status=EvidenceStatus.UNAVAILABLE, source=src)


DROP = StructuredChange(operation=Operation.DROP_COLUMN, target_table="orders", target_column="x")
IDX = StructuredChange(operation=Operation.ADD_INDEX, target_table="orders", index_columns=["x"])


def test_asset_not_found_is_high_and_short_circuits():
    ev = [EvidenceItem(kind=EvidenceKind.ASSET_METADATA, key="orders.x",
                       status=EvidenceStatus.UNAVAILABLE, source="catalog",
                       payload={"reason": "not_found"})]
    a = assess(DROP, ev)
    assert a.category == RiskCategory.HIGH
    assert [f.code for f in a.factors] == ["ASSET_NOT_FOUND"]


def test_primary_key_is_high():
    a = assess(DROP, [_meta(in_primary_key=True)])
    assert a.category == RiskCategory.HIGH
    assert any(f.code == "IN_PRIMARY_KEY" for f in a.factors)


def test_inbound_fk_is_high():
    a = assess(DROP, [_meta(), _dep("foreign_key")])
    assert a.category == RiskCategory.HIGH


def test_view_reference_is_medium():
    a = assess(DROP, [_meta(), _dep("view")])
    assert a.category == RiskCategory.MEDIUM
    assert any(f.code == "REFERENCED_BY_VIEW" for f in a.factors)


def test_actively_read_is_medium():
    a = assess(DROP, [_meta(), _usage(5)])
    assert a.category == RiskCategory.MEDIUM


def test_no_dependents_is_low():
    a = assess(DROP, [_meta(), _usage(0)])
    assert a.category == RiskCategory.LOW
    assert [f.code for f in a.factors] == ["NO_DEPENDENTS_OR_USAGE"]


def test_unavailable_evidence_adds_medium_factor():
    a = assess(DROP, [_meta(), _unavail(EvidenceKind.DOWNSTREAM_USAGE)])
    assert a.category == RiskCategory.MEDIUM
    assert any(f.code == "EVIDENCE_UNAVAILABLE" for f in a.factors)


def test_add_index_low_vs_contention():
    assert assess(IDX, [_meta(), _usage(10)]).category == RiskCategory.LOW
    assert assess(IDX, [_meta(), _usage(500)]).category == RiskCategory.MEDIUM


def test_reproducible():
    ev = [_meta(), _dep("view"), _usage(3)]
    a, b = assess(DROP, ev), assess(DROP, ev)
    assert a.category == b.category
    assert [f.code for f in a.factors] == [f.code for f in b.factors]


def test_every_fired_factor_has_a_readable_description():
    """T071 — SC-001: a reviewer must be able to explain the rating from the factors shown,
    so each factor needs a real sentence, not just a code."""
    cases = [
        (DROP, [EvidenceItem(kind=EvidenceKind.ASSET_METADATA, key="orders.x",
                             status=EvidenceStatus.UNAVAILABLE, source="catalog",
                             payload={"reason": "not_found"})]),
        (DROP, [_meta(in_primary_key=True)]),
        (DROP, [_meta(), _dep("foreign_key")]),
        (DROP, [_meta(), _dep("view")]),
        (DROP, [_meta(), _usage(5)]),
        (DROP, [_meta(), _usage(0)]),
        (DROP, [_meta(), _unavail(EvidenceKind.DOWNSTREAM_USAGE)]),
        (IDX, [_meta(), _usage(10)]),
        (IDX, [_meta(), _usage(500)]),
    ]
    for change, evidence in cases:
        for f in assess(change, evidence).factors:
            desc = f.description.strip()
            assert desc, f.code
            assert desc[0].isupper() or desc[0].isdigit(), f.code
            assert desc.endswith("."), f.code
            assert len(desc.split()) >= 4, f.code
            assert desc.lower() != f.code.lower().replace("_", " "), f.code


def test_evidence_gap_rule_a1():
    # DROP/ALTER + a dependency/usage source unavailable -> gap
    assert has_evidence_gap(DROP, [_meta(), _unavail(EvidenceKind.DEPENDENCY)]) is True
    # ADD_INDEX never gaps
    assert has_evidence_gap(IDX, [_meta(), _unavail(EvidenceKind.DEPENDENCY)]) is False
    # fully obtained -> no gap
    assert has_evidence_gap(DROP, [_meta(), _dep("view"), _usage(1)]) is False
    # asset-not-found is HIGH but not a gap
    nf = [EvidenceItem(kind=EvidenceKind.ASSET_METADATA, key="orders.x",
                       status=EvidenceStatus.UNAVAILABLE, source="catalog",
                       payload={"reason": "not_found"})]
    assert has_evidence_gap(DROP, nf) is False
