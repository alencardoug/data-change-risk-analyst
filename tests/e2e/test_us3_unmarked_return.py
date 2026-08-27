"""T050 — an unmarked RETURN re-drives only the recommendation; risk is unchanged."""

from dcra.graph.build import build_graph, pending_interrupt, resume, run


def test_unmarked_return_keeps_risk_new_recommendation(make_deps, change_request):
    graph = build_graph(make_deps())
    cr = change_request("drop column orders.customer_legacy_id")

    first = pending_interrupt(run(graph, cr))
    risk_before = first["risk"]

    second = pending_interrupt(
        resume(graph, cr.id, {"decision": "RETURN", "reviewer": "owner",
                              "note": "please soften the wording", "evidence_missing": False})
    )
    assert second["risk"] == risk_before  # identical category + factors
    assert second["recommendation"]["version"] == 2
    assert second["recommendation"]["prompted_by_note"] == "please soften the wording"
    assert second["revision_count"] == 1
