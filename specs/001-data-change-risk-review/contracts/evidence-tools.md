# Contract — Evidence Tools (read-only)

Three LangChain `@tool` functions in `src/dcra/evidence/tools.py`. They are the **only** tools
bound to the investigator agent. All are read-only: no writes, no DDL, no arbitrary query.
Each returns a list of `EvidenceItem` (see `data-model.md`).

Common behavior:
- Input is always a resolved `(table, column?)` from the `StructuredChange`, never free text.
- If the tool's logical source name is in `dataset.disabled_sources`, the tool returns a single
  `EvidenceItem(status=UNAVAILABLE, payload=None, source=<name>)` — it never raises for that
  case (FR-024) and never fabricates a payload (FR-004 / Constitution III).
- If the asset/column is not present in the dataset, the tool returns
  `EvidenceItem(kind=ASSET_METADATA, key="<table>.<column>", status=UNAVAILABLE,
  payload={"reason": "not_found"})` for `get_asset_metadata`, and empty lists for the other two.
  The deterministic rules turn "asset metadata not found" into HIGH + factor `ASSET_NOT_FOUND`
  (FR-020).
- Unexpected internal errors are caught at the node boundary and recorded as `UNAVAILABLE`
  with `source` set; they do not crash the graph.

---

## `get_asset_metadata(table: str, column: str | None) -> list[EvidenceItem]`
- **source**: `"catalog"`
- **kind**: `ASSET_METADATA`
- **payload when OBTAINED**: `{ "table": str, "column": str | None, "data_type": str | None,
  "is_nullable": bool | None, "in_primary_key": bool, "in_unique_constraint": bool,
  "row_estimate": int | None }`
- Emits exactly one item (`key = "<table>.<column>"` or `"<table>"`).

## `get_dependencies(table: str, column: str) -> list[EvidenceItem]`
- **source**: `"lineage"`
- **kind**: `DEPENDENCY`
- One item per dependent object. **payload**: `{ "dependent": str, "dependent_type":
  "view" | "materialized_view" | "foreign_key" | "constraint", "columns_referenced": [str] }`
- Empty list ⇒ no known dependents (a real, reproducible fact — not "unavailable").

## `get_downstream_usage(table: str, column: str) -> list[EvidenceItem]`
- **source**: `"usage"`
- **kind**: `DOWNSTREAM_USAGE`
- One item per known consumer. **payload**: `{ "consumer": str, "consumer_type":
  "dashboard" | "job" | "service" | "export", "last_read_at": str | None,
  "reads_per_day": number | None }`
- Empty list ⇒ no recorded usage (reproducible fact).

---

## Determinism

For a fixed dataset state (including `disabled_sources`), each tool is a pure function of its
inputs: same `(table, column)` ⇒ same items in the same order. This is what makes FR-008 and the
unit tier testable without an LLM.
