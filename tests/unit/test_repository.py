"""T019 — AnalysisRecord round-trip (DB-gated: needs DATABASE_URL + reachable Postgres)."""

import os

import pytest

from dcra.domain.enums import Outcome
from dcra.domain.models import AnalysisRecord, ChangeRequest

_DB = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(not _DB, reason="set DATABASE_URL to run repository tests")


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
