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
    from psycopg import Connection
    from psycopg.rows import dict_row

    # Open the connection directly (mirrors PostgresSaver.from_conn_string internals) so its
    # lifetime is tied to the returned saver. Going through the from_conn_string context
    # manager and calling __enter__() would leave the manager unreferenced; it gets finalized
    # immediately, closing the connection before setup() runs.
    conn = Connection.connect(
        database_url, autocommit=True, prepare_threshold=0, row_factory=dict_row
    )
    saver = PostgresSaver(conn, serde=dcra_serde())
    saver.setup()
    return saver
