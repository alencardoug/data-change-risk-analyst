"""V1 (ADR-020) — the graph reads downstream usage through GraphDeps.usage_reader when set.

Deterministic: a stub usage_reader, fake model, MemorySaver. Proves the seam without spawning
the MCP server (that round-trip is covered by test_mcp_usage_tool.py)."""

from dcra.domain.enums import EvidenceKind, EvidenceStatus
from dcra.domain.models import EvidenceItem
from dcra.graph.build import build_graph, pending_interrupt, run


def _stub_usage_reader(calls):
    def _read(table: str, column: str) -> list[EvidenceItem]:
        calls.append((table, column))
        return [
            EvidenceItem(
                kind=EvidenceKind.DOWNSTREAM_USAGE, key="mcp_consumer",
                status=EvidenceStatus.OBTAINED, source="usage",
                payload={"consumer": "mcp_consumer", "consumer_type": "job", "reads_per_day": 3},
            )
        ]

    return _read


def test_collect_usage_uses_the_injected_reader(make_deps, change_request):
    calls: list = []
    deps = make_deps()
    deps.usage_reader = _stub_usage_reader(calls)

    state = run(build_graph(deps), change_request("drop column orders.customer_legacy_id"))

    assert calls == [("orders", "customer_legacy_id")]
    assert any(s.startswith("collect_usage (via MCP):") for s in state["step_log"])
    usage = [e for e in state["evidence"] if e.kind == EvidenceKind.DOWNSTREAM_USAGE]
    assert [e.key for e in usage] == ["mcp_consumer"]
    # risk still computed deterministically from the (MCP-sourced) evidence
    assert pending_interrupt(state) is not None


def test_without_reader_falls_back_to_local(make_deps, change_request):
    state = run(build_graph(make_deps()), change_request("drop column orders.customer_legacy_id"))
    assert any(s.startswith("collect_usage:") for s in state["step_log"])
    assert not any("(via MCP)" in s for s in state["step_log"])
