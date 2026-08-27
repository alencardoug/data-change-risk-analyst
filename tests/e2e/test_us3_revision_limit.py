"""T051 / S6 — the revision loop is bounded: after `limit` returns, only APPROVE/REJECT remain,
and human_review is entered at most limit+1 times (SC-008)."""

from dcra.graph.build import build_graph, pending_interrupt, resume, run


def test_revision_limit_withdraws_return_option(make_deps, change_request):
    graph = build_graph(make_deps(revision_limit=2))
    cr = change_request("drop column orders.customer_legacy_id")

    entries = 0
    payload = pending_interrupt(run(graph, cr))
    entries += 1
    assert "RETURN" in payload["options"] and payload["revisions_remaining"] == 2

    for expected_remaining in (1, 0):
        payload = pending_interrupt(
            resume(graph, cr.id, {"decision": "RETURN", "reviewer": "o", "note": "again",
                                  "evidence_missing": False})
        )
        entries += 1
        assert payload["revisions_remaining"] == expected_remaining

    assert payload["options"] == ["APPROVE", "REJECT"]  # RETURN withdrawn at the limit
    assert entries == 3  # == limit + 1

    out = resume(graph, cr.id, {"decision": "APPROVE", "reviewer": "o"})
    assert out["outcome"].value == "APPROVED"
