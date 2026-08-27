"""T042 — case status progression; no finalize before a review action for MEDIUM/HIGH."""

from dcra.domain.enums import CaseStatus
from dcra.graph.build import (
    build_graph,
    is_awaiting_review,
    pending_interrupt,
    resume,
    run,
)
from tests.conftest import InMemoryRepository


def test_medium_high_progresses_to_awaiting_review_then_finalized(make_deps, change_request):
    repo = InMemoryRepository()
    graph = build_graph(make_deps(repository=repo))
    cr = change_request("drop column orders.customer_legacy_id")

    state = run(graph, cr)
    # paused before the human_review node runs: interrupt raised, node not yet applied
    assert pending_interrupt(state) is not None
    assert is_awaiting_review(graph, cr.id)
    assert cr.id not in repo.saved  # nothing finalized

    out = resume(graph, cr.id, {"decision": "REJECT", "reviewer": "o"})
    assert out["status"] == CaseStatus.FINALIZED

    seen = repo.saved[cr.id].step_log
    assert any(s.startswith("interpret:") for s in seen)
    assert any(s.startswith("assess_risk:") for s in seen)
    assert any(s.startswith("human_review:") for s in seen)
    assert seen[-1].startswith("finalize:")


def test_low_never_enters_awaiting_review(make_deps, change_request):
    repo = InMemoryRepository()
    graph = build_graph(make_deps(repository=repo))
    cr = change_request("add index on orders(customer_id)")
    out = run(graph, cr)
    assert out["status"] == CaseStatus.FINALIZED
    assert "human_review:" not in " ".join(repo.saved[cr.id].step_log)
