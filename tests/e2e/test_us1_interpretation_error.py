"""T026 / S7 — unparseable request → error surfaced, no AnalysisRecord (FR-002)."""

from dcra.graph.build import build_graph, run
from tests.conftest import InMemoryRepository


def test_gibberish_produces_error_no_record(make_deps, change_request):
    repo = InMemoryRepository()
    deps = make_deps(repository=repo)
    state = run(build_graph(deps), change_request("make the thing better"))

    assert state.get("error", "").startswith("interpretation_failed")
    assert state.get("risk") is None
    assert state.get("recommendations", []) == []
    assert repo.saved == {}
