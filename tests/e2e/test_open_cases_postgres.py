"""KNOWN_ISSUES (resolved 2026-09-11) — the "open cases" dropdown against a real PostgresSaver.

DB-gated: needs DATABASE_URL + a reachable Postgres (docker compose up -d).

``PostgresSaver.list(None, ...)`` orders *all* threads' checkpoints together, newest first, so a
paused case falls out of a fixed-size window as soon as a handful of later runs (several
checkpoints each) come in after it. This is the production shape of the bug; the MemorySaver
variant lives in test_reopen_case.py. Runs in a throwaway schema so the shared dev database is
left untouched.
"""

import uuid

import psycopg
import pytest

from dcra.domain.models import ChangeRequest
from dcra.graph.build import build_graph, list_open_cases, run
from dcra.persistence.checkpointer import make_checkpointer
from tests.conftest import (
    InMemoryRepository,
    fake_investigate,
    fake_recommend,
    keyword_interpret,
    reachable_db_url,
)

_DB = reachable_db_url()
pytestmark = pytest.mark.skipif(not _DB, reason="needs a reachable Postgres (docker compose up -d)")


@pytest.fixture
def graph():
    from dcra.evidence.dataset import default_dataset
    from dcra.graph.deps import GraphDeps

    schema = f"open_cases_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(_DB, autocommit=True) as conn:
        conn.execute(f"CREATE SCHEMA {schema}")
    sep = "&" if "?" in _DB else "?"
    saver = make_checkpointer(f"{_DB}{sep}options=-csearch_path%3D{schema}")  # tables land here
    deps = GraphDeps(
        interpret_fn=keyword_interpret,
        recommend_fn=fake_recommend(),
        investigate_fn=fake_investigate(),
        dataset=default_dataset(),
        repository=InMemoryRepository(),
    )
    try:
        yield build_graph(deps, checkpointer=saver)
    finally:
        saver.conn.close()  # the pool
        with psycopg.connect(_DB, autocommit=True) as conn:
            conn.execute(f"DROP SCHEMA {schema} CASCADE")


def _paused(by="alice"):
    return ChangeRequest(raw_text="drop column orders.customer_legacy_id", submitted_by=by)  # MEDIUM


def _finalised(by="bob"):
    return ChangeRequest(raw_text="add index on orders(customer_id)", submitted_by=by)  # LOW


def test_paused_case_survives_later_runs(graph):
    paused = _paused()
    run(graph, paused)
    assert [tid for tid, _ in list_open_cases(graph)] == [paused.id]

    # other users run cases that auto-finalise; each writes several checkpoints newer than
    # anything in the paused thread
    for i in range(6):
        run(graph, _finalised(by=f"user{i}"))

    # a fixed window of 8 raw checkpoints (the old behaviour) now misses it...
    assert list_open_cases(graph, scan=8, max_scan=8) == []
    # ...widening finds it again (and the default window would too)
    assert [tid for tid, _ in list_open_cases(graph, scan=8)] == [paused.id]
    assert [tid for tid, _ in list_open_cases(graph)] == [paused.id]


def test_newest_open_cases_first_and_limit(graph):
    open_ids = []
    for i in range(4):
        for j in range(2):
            run(graph, _finalised(by=f"noise{i}{j}"))
        cr = _paused(by=f"owner{i}")
        run(graph, cr)
        open_ids.append(cr.id)
    newest_first = open_ids[::-1]

    assert [tid for tid, _ in list_open_cases(graph, scan=8)] == newest_first
    # `limit` keeps the newest ones; `min_open` is clamped to it
    assert [tid for tid, _ in list_open_cases(graph, scan=8, limit=2)] == newest_first[:2]
    # the cap bounds the walk: a window not allowed to grow only reaches the newest one
    assert [tid for tid, _ in list_open_cases(graph, scan=8, max_scan=8)] == newest_first[:1]
