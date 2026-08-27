"""A tiny local MCP server exposing ONE domain evidence tool over stdio (ADR-020, V1).

Run:  python -m dcra.mcp.server

This is deliberately the smallest possible MCP surface — a single read-only tool — so the
learning point is the *interoperability boundary* (client/server/transport), not a second
orchestration layer. The graph still owns the workflow; MCP only moves where one tool lives.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from dcra.evidence.dataset import default_dataset
from dcra.evidence.tools import read_downstream_usage

mcp = FastMCP("dcra-evidence")


@mcp.tool()
def get_downstream_usage(table: str, column: str) -> list[dict]:
    """Known downstream consumers (dashboards, jobs, services) that read table.column."""
    items = read_downstream_usage(default_dataset(), table, column)
    return [i.model_dump(mode="json") for i in items]


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
