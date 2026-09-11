"""T069 (Phase 7 / converge) — the mechanism behind the Streamlit "Reopen a case by id" button:
load a paused case by thread_id, rebuild the review payload, resume to a final record."""

from dcra.graph.build import (
    build_graph,
    get_state,
    is_awaiting_review,
    list_open_cases,
    resume,
    run,
)
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


def test_list_open_cases_survives_later_runs(make_deps, change_request):
    """KNOWN_ISSUES (resolved 2026-09-11): a paused case must not vanish from the "open cases"
    dropdown just because later runs pushed its checkpoints past a fixed scan window."""
    graph = build_graph(make_deps(repository=InMemoryRepository()))
    # MemorySaver enumerates threads in insertion order, so auto-finalised cases created first
    # fill the initial window and the paused case is only reached by widening it.
    for i in range(8):
        run(graph, change_request("add index on orders(customer_id)", by=f"user{i}"))
    paused = change_request("drop column orders.customer_legacy_id")
    run(graph, paused)

    # a fixed window (the old behaviour) misses it...
    assert list_open_cases(graph, scan=8, max_scan=8) == []
    # ...widening finds it, and nothing else is open
    got = list_open_cases(graph, scan=8)
    assert [tid for tid, _ in got] == [paused.id]
    assert got[0][1] == "drop column orders.customer_legacy_id · MEDIUM · data.engineer"


def test_list_open_cases_finds_at_least_min_open_newest_first(make_deps, change_request):
    graph = build_graph(make_deps(repository=InMemoryRepository()))
    open_ids = []
    for i in range(4):
        for j in range(3):  # finalised noise between the open cases
            run(graph, change_request("add index on orders(customer_id)", by=f"noise{i}{j}"))
        cr = change_request("drop column orders.customer_legacy_id", by=f"owner{i}")
        run(graph, cr)
        open_ids.append(cr.id)

    got = [tid for tid, _ in list_open_cases(graph, scan=8, min_open=3, limit=5)]
    assert len(got) >= 3
    assert got == sorted(got, key=open_ids.index, reverse=True)  # newest first
    assert set(got) <= set(open_ids)
