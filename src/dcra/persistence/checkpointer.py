"""PostgresSaver construction (ADR-012). Falls back to MemorySaver when no DATABASE_URL."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any


@contextmanager
def open_checkpointer(database_url: str | None):
    """Yield a checkpointer. With a URL, a PostgresSaver (tables ensured via .setup())."""
    from dcra.persistence.serde import dcra_serde

    if not database_url:
        from langgraph.checkpoint.memory import MemorySaver

        yield MemorySaver(serde=dcra_serde())
        return

    from langgraph.checkpoint.postgres import PostgresSaver

    with PostgresSaver.from_conn_string(database_url) as saver:
        saver.serde = dcra_serde()
        saver.setup()
        yield saver


def make_checkpointer(database_url: str | None) -> Any:
    """Non-context variant for long-lived apps (Streamlit). Caller keeps the connection open."""
    from dcra.persistence.serde import dcra_serde

    if not database_url:
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver(serde=dcra_serde())

    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    # A pool (not a single bare connection) so a connection dropped underneath us — an idle
    # Neon compute suspending, Cloud SQL recycling, a network blip — is discarded and replaced
    # on the next checkout instead of wedging the app until restart. `check` does a cheap
    # pre-ping per checkout; `min_size=0` + `max_idle` keep no connection open into a suspended
    # Neon instance. Opening via the constructor (`open=True`) is fine and lifetime-bound to
    # the returned saver, which the caller keeps for the process lifetime.
    pool = ConnectionPool(
        conninfo=database_url,
        min_size=0,
        max_size=4,
        max_idle=120.0,
        check=ConnectionPool.check_connection,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=True,
    )
    saver = PostgresSaver(pool, serde=dcra_serde())
    saver.setup()
    return saver
