"""T025 / S5 — asset absent from the evidence source → HIGH + ASSET_NOT_FOUND factor,
no fabrication. (US1 scope: graph ends after `recommend`; the gate-reach assertion is T065.)"""

from dcra.domain.enums import RiskCategory
from dcra.graph.build import build_graph, run
from tests.conftest import InMemoryRepository


def test_unknown_asset_is_high_no_fabrication(make_deps, change_request):
    repo = InMemoryRepository()
    deps = make_deps(repository=repo)
    state = run(build_graph(deps), change_request("drop column orders.legacy_region"))

    assert state["risk"].category == RiskCategory.HIGH
    assert [f.code for f in state["risk"].factors] == ["ASSET_NOT_FOUND"]
    assert state.get("evidence_gap") is False  # a missing asset is not an investigatable gap

    meta = [e for e in state["evidence"] if e.kind.value == "ASSET_METADATA"][0]
    assert meta.status.value == "UNAVAILABLE"
    assert meta.payload == {"reason": "not_found"}  # nothing invented

    # US1 scope: non-LOW ends without finalizing, so no record yet
    assert repo.saved == {}
