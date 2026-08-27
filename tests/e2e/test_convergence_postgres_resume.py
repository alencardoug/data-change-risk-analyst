"""T067 (Phase 7 / converge) — restart-safe resume proven with PostgresSaver, not MemorySaver.

DB-gated: needs DATABASE_URL + a reachable Postgres (docker compose up -d).

The first checkpointer context is fully closed (connection released) before a brand-new
checkpointer + graph pick the case up by thread_id — the closest a single test process gets to
"the application was fully restarted" (SC-005 / FR-012).
"""

import os
import uuid

import pytest

from dcra.domain.enums import CaseStatus, Outcome
from dcra.domain.models import ChangeRequest
from dcra.graph.build import build_graph, pending_interrupt, resume, run
from dcra.persistence.checkpointer import open_checkpointer
from tests.conftest import InMemoryRepository, fake_investigate, fake_recommend, keyword_interpret

_DB = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(not _DB, reason="set DATABASE_URL to run Postgres resume test")


def _deps(repo):
    from dcra.evidence.dataset import default_dataset
    from dcra.graph.deps import GraphDeps

    return GraphDeps(
        interpret_fn=keyword_interpret,
        recommend_fn=fake_recommend(),
        investigate_fn=fake_investigate(),
        dataset=default_dataset(),
        repository=repo,
    )


def test_resume_across_checkpointer_reopen():
    repo = InMemoryRepository()
    deps = _deps(repo)
    cr = ChangeRequest(
        id=f"conv-{uuid.uuid4()}",
        raw_text="drop column orders.customer_legacy_id",
        submitted_by="eng",
    )

    with open_checkpointer(_DB) as cp1:
        state = run(build_graph(deps, checkpointer=cp1), cr)
        assert pending_interrupt(state) is not None
        assert cr.id not in repo.saved
    # cp1 (and its connection) is now closed

    with open_checkpointer(_DB) as cp2:
        out = resume(build_graph(deps, checkpointer=cp2), cr.id, {
            "decision": "APPROVE", "reviewer": "data.owner",
        })

    assert out["status"] == CaseStatus.FINALIZED
    assert out["outcome"] == Outcome.APPROVED
    assert repo.saved[cr.id].reviewed is True
