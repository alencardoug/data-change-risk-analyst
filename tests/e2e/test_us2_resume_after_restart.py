"""T041 / S8 — a run paused for review resumes after the graph object is rebuilt (FR-012, SC-005).

The persistence layer is the checkpointer: we drop the compiled graph and build a fresh one
against the SAME checkpointer + thread_id, then resume.
"""

from dcra.domain.enums import CaseStatus, Outcome
from dcra.graph.build import build_graph, is_awaiting_review, pending_interrupt, resume, run
from tests.conftest import InMemoryRepository


def test_resume_after_graph_rebuild(make_deps, change_request, checkpointer):
    repo = InMemoryRepository()
    deps = make_deps(repository=repo)

    cr = change_request("drop column orders.customer_legacy_id")
    state = run(build_graph(deps, checkpointer=checkpointer), cr)
    assert pending_interrupt(state) is not None
    assert is_awaiting_review(build_graph(deps, checkpointer=checkpointer), cr.id)

    # drop that graph object; a brand-new one shares only the checkpointer
    fresh = build_graph(deps, checkpointer=checkpointer)
    out = resume(fresh, cr.id, {"decision": "APPROVE", "reviewer": "owner"})

    assert out["status"] == CaseStatus.FINALIZED
    assert out["outcome"] == Outcome.APPROVED
    assert repo.saved[cr.id].reviewed is True
