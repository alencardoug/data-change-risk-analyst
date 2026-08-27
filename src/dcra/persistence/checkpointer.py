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

    with PostgresSaver.from_conn_string(database_url, serde=dcra_serde()) as saver:
        saver.setup()
        yield saver


def make_checkpointer(database_url: str | None) -> Any:
    """Non-context variant for long-lived apps (Streamlit). Caller keeps the connection open."""
    from dcra.persistence.serde import dcra_serde

    if not database_url:
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver(serde=dcra_serde())
    from langgraph.checkpoint.postgres import PostgresSaver

    saver = PostgresSaver.from_conn_string(database_url, serde=dcra_serde()).__enter__()
    saver.setup()
    return saver
