"""T021 — GraphState reducers."""

from dcra.domain.enums import EvidenceKind, EvidenceStatus
from dcra.domain.models import EvidenceItem
from dcra.graph.state import append_list, merge_evidence


def _e(kind: EvidenceKind, key: str) -> EvidenceItem:
    return EvidenceItem(kind=kind, key=key, status=EvidenceStatus.OBTAINED, source="s",
                        payload={"k": key})


def test_merge_evidence_dedupes_first_write_and_sorts():
    a = [_e(EvidenceKind.DEPENDENCY, "z"), _e(EvidenceKind.ASSET_METADATA, "m")]
    b = [_e(EvidenceKind.DEPENDENCY, "z"), _e(EvidenceKind.DOWNSTREAM_USAGE, "u")]
    merged = merge_evidence(a, b)
    keys = [(e.kind.value, e.key) for e in merged]
    assert keys == sorted(keys)
    assert keys.count(("DEPENDENCY", "z")) == 1


def test_merge_evidence_order_independent():
    a = [_e(EvidenceKind.DEPENDENCY, "a"), _e(EvidenceKind.DEPENDENCY, "b")]
    b = [_e(EvidenceKind.DEPENDENCY, "b"), _e(EvidenceKind.DEPENDENCY, "a")]
    assert [e.key for e in merge_evidence(a, b)] == [e.key for e in merge_evidence(b, a)]


def test_merge_evidence_handles_none():
    assert merge_evidence(None, [_e(EvidenceKind.DEPENDENCY, "a")])[0].key == "a"
    assert merge_evidence([_e(EvidenceKind.DEPENDENCY, "a")], None)[0].key == "a"


def test_append_list():
    assert append_list(["a"], ["b", "c"]) == ["a", "b", "c"]
    assert append_list(None, ["b"]) == ["b"]
