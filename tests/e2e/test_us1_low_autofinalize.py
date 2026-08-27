"""T023 / S1 — LOW risk auto-finalizes into one record, no human review."""

from dcra.domain.enums import CaseStatus, Outcome, RiskCategory
from dcra.graph.build import build_graph, run
from tests.conftest import InMemoryRepository


def test_low_risk_auto_finalizes(make_deps, change_request):
    repo = InMemoryRepository()
    deps = make_deps(repository=repo)
    state = run(build_graph(deps), change_request("add index on orders(customer_id)"))

    assert state["risk"].category == RiskCategory.LOW
    assert state["status"] == CaseStatus.FINALIZED
    assert state["outcome"] == Outcome.AUTO_FINALIZED

    (record,) = list(repo.saved.values())
    assert record.reviewed is False
    assert record.outcome == Outcome.AUTO_FINALIZED
    assert len(record.recommendations) == 1
    assert record.final_recommendation_version == 1
    # step_log is an ordered account (FR-021)
    assert record.step_log[0].startswith("interpret:")
    assert record.step_log[-1].startswith("finalize:")
    assert any(s.startswith("assess_risk:") for s in record.step_log)
