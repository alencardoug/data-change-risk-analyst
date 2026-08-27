"""Client side of the V1 MCP increment (ADR-020).

``read_downstream_usage_via_mcp(table, column)`` connects to the local MCP server
(``python -m dcra.mcp.server`` over stdio), calls its one tool, and maps the result to
``EvidenceItem``s — the same shape the local reader produces.

If the MCP server is unreachable or errors, this returns a single ``UNAVAILABLE`` item: an
absent MCP server degrades exactly like a disabled evidence source (FR-024), never a crash.
"""

from __future__ import annotations

import asyncio
import json
import sys

from dcra.domain.enums import EvidenceKind, EvidenceStatus
from dcra.domain.models import EvidenceItem

_SERVER = {
    "dcra-evidence": {
        "command": sys.executable,
        "args": ["-m", "dcra.mcp.server"],
        "transport": "stdio",
    }
}


def _unavailable(table: str, column: str) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            kind=EvidenceKind.DOWNSTREAM_USAGE,
            key=f"{table}.{column}",
            status=EvidenceStatus.UNAVAILABLE,
            source="usage",
        )
    ]


def _parse(raw) -> list[EvidenceItem]:
    """MCP tool results arrive as content blocks: a list of {'type':'text','text': <json>}.
    Each text block is one EvidenceItem (or a JSON array of them)."""
    payloads: list = []
    if isinstance(raw, str):
        payloads = json.loads(raw) if raw.strip() else []
    else:
        for block in raw or []:
            text = block.get("text") if isinstance(block, dict) else None
            if not text:
                continue
            obj = json.loads(text)
            payloads.extend(obj if isinstance(obj, list) else [obj])
    if isinstance(payloads, dict):
        payloads = [payloads]
    return [EvidenceItem.model_validate(d) for d in payloads]


async def _fetch(table: str, column: str) -> list[EvidenceItem]:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(_SERVER)
    tools = await client.get_tools()
    tool = next(t for t in tools if t.name == "get_downstream_usage")
    return _parse(await tool.ainvoke({"table": table, "column": column}))


def read_downstream_usage_via_mcp(table: str, column: str) -> list[EvidenceItem]:
    try:
        return asyncio.run(_fetch(table, column))
    except Exception:
        return _unavailable(table, column)
