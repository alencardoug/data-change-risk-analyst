"""T065 — analyze finding G1: with US2 wiring, HIGH / reduced-confidence cases reach the
human_review gate (FR-020, FR-024, SC-009)."""

from dcra.graph.build import build_graph, pending_interrupt, run
from tests.conftest import InMemoryRepository


def test_unknown_asset_reaches_gate_with_factor_in_payload(make_deps, change_request):
    repo = InMemoryRepository()
    graph = build_graph(make_deps(repository=repo))
    cr = change_request("drop column orders.legacy_region")  # absent asset

    payload = pending_interrupt(run(graph, cr))
    assert payload is not None
    assert payload["risk"]["category"] == "HIGH"
    codes = [f["code"] for f in payload["risk"]["factors"]]
    assert "ASSET_NOT_FOUND" in codes
    assert cr.id not in repo.saved  # no record before a decision


def test_disabled_source_reaches_gate_with_reduced_confidence(make_deps, change_request):
    repo = InMemoryRepository()
    graph = build_graph(make_deps(repository=repo, disabled_sources={"usage"}))
    cr = change_request("alter column orders.status")

    payload = pending_interrupt(run(graph, cr))
    assert payload is not None
    assert payload["recommendation"]["confidence"] == "REDUCED"
    assert any(e["status"] == "UNAVAILABLE" for e in payload["evidence"])
    # approval is offered — not auto-blocked (FR-024)
    assert "APPROVE" in payload["options"]
