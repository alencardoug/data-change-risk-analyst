"""T019 — AnalysisRecord round-trip (DB-gated: needs DATABASE_URL + reachable Postgres)."""

import pytest

from dcra.domain.enums import Outcome
from dcra.domain.models import AnalysisRecord, ChangeRequest
from tests.conftest import reachable_db_url

_DB = reachable_db_url()
pytestmark = pytest.mark.skipif(not _DB, reason="needs a reachable Postgres (docker compose up -d)")


@pytest.fixture
def repo():
    from dcra.persistence.repository import PostgresRepository

    r = PostgresRepository(_DB)
    r.setup()
    return r


def test_round_trip(repo):
    cr = ChangeRequest(raw_text="drop column orders.notes_internal", submitted_by="t")
    rec = AnalysisRecord(
        id=cr.id, change_request=cr, outcome=Outcome.AUTO_FINALIZED,
        final_recommendation_version=1, step_log=["a", "b"],
    )
    repo.save(rec)
    got = repo.get(cr.id)
    assert got is not None
    assert got.id == cr.id
    assert got.outcome == Outcome.AUTO_FINALIZED
    assert got.step_log == ["a", "b"]


def test_get_unknown_returns_none(repo):
    assert repo.get("no-such-id") is None
