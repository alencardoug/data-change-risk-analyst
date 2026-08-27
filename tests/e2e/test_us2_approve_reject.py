"""T040 / S2 — human review gate: approve and reject paths."""

from dcra.domain.enums import Outcome
from dcra.graph.build import build_graph, pending_interrupt, resume, run
from tests.conftest import InMemoryRepository

CHANGE = "drop column orders.customer_legacy_id"  # MEDIUM in the default dataset


def _run_to_gate(make_deps, change_request):
    repo = InMemoryRepository()
    graph = build_graph(make_deps(repository=repo))
    cr = change_request(CHANGE)
    state = run(graph, cr)
    return repo, graph, cr, state


def test_gate_payload_and_no_record_before_decision(make_deps, change_request):
    repo, _graph, cr, state = _run_to_gate(make_deps, change_request)
    payload = pending_interrupt(state)
    assert payload is not None
    assert payload["risk"]["category"] == "MEDIUM"
    assert payload["recommendation"]["ai_generated"] is True
    assert set(payload["options"]) >= {"APPROVE", "REJECT"}
    assert payload["evidence"]
    assert cr.id not in repo.saved  # nothing finalised yet


def test_approve_finalises_approved(make_deps, change_request):
    repo, graph, cr, _state = _run_to_gate(make_deps, change_request)
    out = resume(graph, cr.id, {"decision": "APPROVE", "reviewer": "data.owner"})
    assert out["outcome"] == Outcome.APPROVED
    rec = repo.saved[cr.id]
    assert rec.reviewed is True
    assert rec.outcome == Outcome.APPROVED
    # AI recommendation and human decision are separate fields (FR-018)
    assert rec.recommendations and rec.recommendations[-1].ai_generated is True
    assert [a.decision.value for a in rec.review_actions] == ["APPROVE"]
    assert rec.review_actions[-1].reviewer == "data.owner"


def test_reject_finalises_rejected(make_deps, change_request):
    repo, graph, cr, _state = _run_to_gate(make_deps, change_request)
    out = resume(graph, cr.id, {"decision": "REJECT", "reviewer": "data.owner"})
    assert out["outcome"] == Outcome.REJECTED
    assert repo.saved[cr.id].outcome == Outcome.REJECTED
