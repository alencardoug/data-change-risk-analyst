# V1 increment — one evidence tool via MCP

**Status**: implemented on branch `002-v1-mcp-and-cleanup` (ADR-020). Off by default.

## What changed (before → after)

| | V0 | V1 (`DCRA_USAGE_VIA_MCP=1`) |
|---|---|---|
| `get_asset_metadata`, `get_dependencies` | local `@tool` functions | unchanged — still local |
| **downstream usage read** | `read_downstream_usage(dataset, …)` called directly by the `collect_usage` node | the `collect_usage` node calls `GraphDeps.usage_reader`, which is `read_downstream_usage_via_mcp` → a **stdio MCP client** talking to `python -m dcra.mcp.server` |
| step log | `collect_usage: N item(s)` | `collect_usage (via MCP): N item(s)` |
| server down / unreachable | n/a | one `EvidenceItem(status=UNAVAILABLE, source="usage")` — degrades exactly like a disabled source (FR-024), never a crash |

Nothing else moves. The graph, the risk rules, the review gate, the record — all identical. The
MCP-sourced usage items are byte-for-byte the same as the local reader's (a test asserts this).

## Run it

```bash
DCRA_USAGE_VIA_MCP=1 uv run streamlit run src/dcra/app/streamlit_app.py
# the server is spawned per read as a stdio subprocess; nothing to start by hand
python -m dcra.mcp.server        # (optional) run the server standalone to inspect it
```

## Files

| Path | Role |
|---|---|
| `src/dcra/mcp/server.py` | `FastMCP("dcra-evidence")` with ONE tool, `get_downstream_usage`, over stdio |
| `src/dcra/mcp/client.py` | `read_downstream_usage_via_mcp(table, column)` — `MultiServerMCPClient` (stdio) → tool call → `EvidenceItem`s; any failure → `UNAVAILABLE` |
| `src/dcra/graph/deps.py` | `GraphDeps.usage_reader` — the swap point; `production_deps` sets it when `settings.usage_via_mcp` |
| `tests/mcp/` | round-trip vs the local reader; graceful "server unavailable"; the graph seam with a stub reader |

## What MCP adds here — and what it does not

- **Adds**: an interoperability boundary. `get_downstream_usage` is now a process-separated
  capability with a wire protocol (JSON-RPC over stdio), a lifecycle (spawn / initialize /
  list-tools / call / shutdown), and its own failure mode. Any MCP-speaking client — not just
  this app — could consume it.
- **Does not add**: orchestration. MCP is not a workflow engine; LangGraph still owns state,
  routing, the interrupt, and the loop. MCP did not replace LangChain, LangGraph, the database,
  or an API — it only changed *where one tool executes* and *how it is reached*.

## Interview-defensible points

- "Why only one tool via MCP?" — the smallest change that demonstrates the client/server/
  transport boundary without inflating the V0 or adding operational weight. The other two tools
  stay local, so the before/after is visible in one diff and one step-log line.
- "What happens if the MCP server dies?" — the client catches it and returns an `UNAVAILABLE`
  evidence item; the risk rules already have an `EVIDENCE_UNAVAILABLE` factor and the
  recommendation confidence drops to `REDUCED` (FR-024). The workflow still reaches the human
  review gate.
- "Local function vs MCP tool vs LangChain tool?" — a local function is an in-process call; a
  LangChain `@tool` wraps a callable with a schema for the model; an MCP tool is a
  *remote* capability reached over a protocol, discovered at runtime via `list-tools`.
