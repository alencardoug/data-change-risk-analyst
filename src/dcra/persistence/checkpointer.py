"""PostgresSaver construction (ADR-012). Falls back to MemorySaver when no DATABASE_URL."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any


@contextmanager
def open_checkpointer(database_url: str | None):
    """Yield a checkpointer. With a URL, a PostgresSaver (tables ensured via .setup())."""
    if not database_url:
        from langgraph.checkpoint.memory import MemorySaver

        yield MemorySaver()
        return

    from langgraph.checkpoint.postgres import PostgresSaver

    with PostgresSaver.from_conn_string(database_url) as saver:
        saver.setup()
        yield saver


def make_checkpointer(database_url: str | None) -> Any:
    """Non-context variant for long-lived apps (Streamlit). Caller keeps the connection open."""
    if not database_url:
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()
    from langgraph.checkpoint.postgres import PostgresSaver

    saver = PostgresSaver.from_conn_string(database_url).__enter__()
    saver.setup()
    return saver
