"""V1 (ADR-020) — the downstream-usage evidence read through the local MCP server.

Hermetic: spawns `python -m dcra.mcp.server` over stdio. No API key, no network.
"""

import dcra.mcp.client as mcp_client
from dcra.evidence.dataset import default_dataset
from dcra.evidence.tools import read_downstream_usage
from dcra.mcp.client import read_downstream_usage_via_mcp


def _dump(items):
    return [i.model_dump(mode="json") for i in items]


def test_mcp_reader_matches_local_reader():
    for table, column in [
        ("orders", "customer_legacy_id"),
        ("orders", "status"),
        ("orders", "ghost"),  # unknown → empty, a reproducible fact (not "unavailable")
    ]:
        via_mcp = read_downstream_usage_via_mcp(table, column)
        local = read_downstream_usage(default_dataset(), table, column)
        assert _dump(via_mcp) == _dump(local), f"{table}.{column}"


def test_mcp_server_unavailable_degrades_to_unavailable(monkeypatch):
    """An absent MCP server behaves like a disabled evidence source (FR-024), never a crash."""
    broken = {
        "dcra-evidence": {
            "command": mcp_client._SERVER["dcra-evidence"]["command"],
            "args": ["-m", "dcra.mcp.__no_such_module__"],
            "transport": "stdio",
        }
    }
    monkeypatch.setattr(mcp_client, "_SERVER", broken)
    items = read_downstream_usage_via_mcp("orders", "status")
    assert len(items) == 1
    assert items[0].status.value == "UNAVAILABLE"
    assert items[0].payload is None  # nothing fabricated
