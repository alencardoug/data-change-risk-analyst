"""T012 — read-only evidence tool contract."""

from dcra.domain.enums import EvidenceStatus
from dcra.evidence.dataset import default_dataset
from dcra.evidence.tools import (
    make_evidence_tools,
    read_asset_metadata,
    read_dependencies,
    read_downstream_usage,
)


def test_obtained_payloads():
    ds = default_dataset()
    meta = read_asset_metadata(ds, "orders", "customer_legacy_id")
    assert len(meta) == 1 and meta[0].status == EvidenceStatus.OBTAINED
    assert meta[0].payload["data_type"] == "varchar"
    deps = read_dependencies(ds, "orders", "customer_legacy_id")
    assert {d.payload["dependent_type"] for d in deps} == {"view"}
    usage = read_downstream_usage(ds, "orders", "customer_legacy_id")
    assert usage and usage[0].status == EvidenceStatus.OBTAINED


def test_disabled_source_returns_unavailable_never_raises():
    ds = default_dataset(disabled_sources={"usage"})
    usage = read_downstream_usage(ds, "orders", "status")
    assert len(usage) == 1 and usage[0].status == EvidenceStatus.UNAVAILABLE
    assert usage[0].payload is None


def test_missing_asset_not_found_and_empty_lineage():
    ds = default_dataset()
    meta = read_asset_metadata(ds, "orders", "ghost")
    assert meta[0].status == EvidenceStatus.UNAVAILABLE
    assert meta[0].payload == {"reason": "not_found"}
    assert read_dependencies(ds, "orders", "ghost") == []
    assert read_downstream_usage(ds, "orders", "ghost") == []


def test_determinism():
    ds = default_dataset()
    a = [e.model_dump() for e in read_dependencies(ds, "orders", "customer_legacy_id")]
    b = [e.model_dump() for e in read_dependencies(ds, "orders", "customer_legacy_id")]
    assert a == b


def test_agent_tools_are_three_readonly():
    tools = make_evidence_tools(default_dataset())
    assert [t.name for t in tools] == [
        "get_asset_metadata", "get_dependencies", "get_downstream_usage"
    ]
    out = tools[0].invoke({"table": "orders", "column": "customer_legacy_id"})
    assert out[0]["status"] == "OBTAINED"
