"""T069 (Phase 7 / converge) — the mechanism behind the Streamlit "Reopen a case by id" button:
load a paused case by thread_id, rebuild the review payload, resume to a final record."""

from dcra.graph.build import build_graph, get_state, is_awaiting_review, resume, run
from dcra.graph.nodes import review_payload
from tests.conftest import InMemoryRepository


def test_reopen_paused_case_and_resume(make_deps, change_request):
    repo = InMemoryRepository()
    deps = make_deps(repository=repo)
    graph = build_graph(deps)
    cr = change_request("drop column orders.customer_legacy_id")
    run(graph, cr)  # pauses at the gate

    # what the "Reopen" button does with only a thread_id in hand:
    state = get_state(graph, cr.id)
    assert is_awaiting_review(graph, cr.id)
    payload = review_payload(state, limit=deps.revision_limit)
    assert payload["risk"]["category"] == "MEDIUM"
    assert "APPROVE" in payload["options"]

    out = resume(graph, cr.id, {"decision": "APPROVE", "reviewer": "reopened.owner"})
    assert out["outcome"].value == "APPROVED"
    assert repo.saved[cr.id].review_actions[-1].reviewer == "reopened.owner"


def test_reopen_already_finalized_case(make_deps, change_request):
    repo = InMemoryRepository()
    graph = build_graph(make_deps(repository=repo))
    cr = change_request("add index on orders(customer_id)")  # LOW → auto-finalized
    run(graph, cr)

    state = get_state(graph, cr.id)
    assert not is_awaiting_review(graph, cr.id)
    assert state["outcome"].value == "AUTO_FINALIZED"
