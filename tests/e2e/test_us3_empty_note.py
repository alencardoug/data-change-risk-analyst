"""T066 — analyze finding G2 (FR-016): a blank / whitespace-only return note does not consume a
revision cycle and creates no new recommendation version."""

import pytest
from pydantic import ValidationError

from dcra.graph.build import build_graph, pending_interrupt, resume, run


def test_blank_note_is_rejected_and_costs_no_cycle(make_deps, change_request):
    graph = build_graph(make_deps())
    cr = change_request("drop column orders.customer_legacy_id")

    before = pending_interrupt(run(graph, cr))
    assert before["revision_count"] == 0
    assert "RETURN" in before["options"]

    # a whitespace-only RETURN never validates into a ReviewAction: no state change at all
    with pytest.raises(ValidationError):
        resume(graph, cr.id, {"decision": "RETURN", "reviewer": "o", "note": "   ",
                              "evidence_missing": False})

    # the gate still stands; a subsequent substantive return is the first that counts
    after = pending_interrupt(
        resume(graph, cr.id, {"decision": "RETURN", "reviewer": "o",
                              "note": "a real, substantive reason", "evidence_missing": False})
    )
    assert after["revision_count"] == 1
    assert after["recommendation"]["version"] == 2
