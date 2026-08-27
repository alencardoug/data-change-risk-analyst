"""T024 / S4 — a disabled evidence source: analysis still completes, confidence REDUCED,
investigator runs on the gap (FR-010, FR-024, SC-003)."""

from dcra.domain.enums import Confidence, EvidenceStatus, RiskCategory
from dcra.graph.build import build_graph, run


def test_evidence_source_unavailable(make_deps, change_request):
    deps = make_deps(disabled_sources={"usage"})
    state = run(build_graph(deps), change_request("alter column orders.status"))

    usage_items = [e for e in state["evidence"] if e.kind.value == "DOWNSTREAM_USAGE"]
    assert usage_items and all(e.status == EvidenceStatus.UNAVAILABLE for e in usage_items)

    # the A1 gate fired and the investigator step ran
    assert any(s.startswith("investigate:") for s in state["step_log"])

    rec = state["recommendations"][-1]
    assert rec.confidence == Confidence.REDUCED
    assert state["risk"].category in (RiskCategory.MEDIUM, RiskCategory.HIGH)
    # not auto-blocked: a recommendation exists and the run did not error
    assert state.get("error") is None
