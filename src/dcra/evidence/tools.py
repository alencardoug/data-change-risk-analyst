"""Read-only evidence tools. Contract: specs/001-data-change-risk-review/contracts/evidence-tools.md.

Two shapes:
* pure functions ``read_*`` (dataset-first) used directly by the collector nodes;
* ``make_evidence_tools(dataset)`` returns LangChain ``@tool`` wrappers for the investigator agent.

No tool writes, runs DDL, or executes arbitrary queries. A disabled source or a missing asset
yields an ``UNAVAILABLE`` EvidenceItem; it never raises for those cases and never fabricates a
payload (FR-004 / FR-020 / Constitution III).
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from dcra.domain.enums import EvidenceKind, EvidenceStatus
from dcra.domain.models import EvidenceItem
from dcra.evidence.dataset import (
    SOURCE_CATALOG,
    SOURCE_LINEAGE,
    SOURCE_USAGE,
    Dataset,
)


def _unavailable(kind: EvidenceKind, key: str, source: str, reason: str | None = None) -> EvidenceItem:
    return EvidenceItem(
        kind=kind,
        key=key,
        status=EvidenceStatus.UNAVAILABLE,
        source=source,
        payload={"reason": reason} if reason else None,
    )


def read_asset_metadata(dataset: Dataset, table: str, column: str | None) -> list[EvidenceItem]:
    key = f"{table}.{column}" if column else table
    if dataset.source_disabled(SOURCE_CATALOG):
        return [_unavailable(EvidenceKind.ASSET_METADATA, key, SOURCE_CATALOG)]
    facts = dataset.get(table, column)
    if facts is None:
        return [_unavailable(EvidenceKind.ASSET_METADATA, key, SOURCE_CATALOG, reason="not_found")]
    return [
        EvidenceItem(
            kind=EvidenceKind.ASSET_METADATA,
            key=key,
            status=EvidenceStatus.OBTAINED,
            source=SOURCE_CATALOG,
            payload={
                "table": table,
                "column": column,
                "data_type": facts.data_type,
                "is_nullable": facts.is_nullable,
                "in_primary_key": facts.in_primary_key,
                "in_unique_constraint": facts.in_unique_constraint,
                "row_estimate": facts.row_estimate,
            },
        )
    ]


def read_dependencies(dataset: Dataset, table: str, column: str) -> list[EvidenceItem]:
    key = f"{table}.{column}"
    if dataset.source_disabled(SOURCE_LINEAGE):
        return [_unavailable(EvidenceKind.DEPENDENCY, key, SOURCE_LINEAGE)]
    facts = dataset.get(table, column)
    if facts is None:
        return []  # no known dependents for an unknown asset (a reproducible fact)
    return [
        EvidenceItem(
            kind=EvidenceKind.DEPENDENCY,
            key=dep["dependent"],
            status=EvidenceStatus.OBTAINED,
            source=SOURCE_LINEAGE,
            payload=dep,
        )
        for dep in facts.dependencies
    ]


def read_downstream_usage(dataset: Dataset, table: str, column: str) -> list[EvidenceItem]:
    key = f"{table}.{column}"
    if dataset.source_disabled(SOURCE_USAGE):
        return [_unavailable(EvidenceKind.DOWNSTREAM_USAGE, key, SOURCE_USAGE)]
    facts = dataset.get(table, column)
    if facts is None:
        return []
    return [
        EvidenceItem(
            kind=EvidenceKind.DOWNSTREAM_USAGE,
            key=u["consumer"],
            status=EvidenceStatus.OBTAINED,
            source=SOURCE_USAGE,
            payload=u,
        )
        for u in facts.usage
    ]


def make_evidence_tools(dataset: Dataset) -> list[BaseTool]:
    """LangChain tools for the investigator agent (read-only)."""

    @tool
    def get_asset_metadata(table: str, column: str | None = None) -> list[dict]:
        """Return catalog metadata for a table or table.column (data type, nullability, keys)."""
        return [e.model_dump(mode="json") for e in read_asset_metadata(dataset, table, column)]

    @tool
    def get_dependencies(table: str, column: str) -> list[dict]:
        """Return objects (views, FKs, constraints) that reference the given table.column."""
        return [e.model_dump(mode="json") for e in read_dependencies(dataset, table, column)]

    @tool
    def get_downstream_usage(table: str, column: str) -> list[dict]:
        """Return known downstream consumers (dashboards, jobs, services) that read table.column."""
        return [e.model_dump(mode="json") for e in read_downstream_usage(dataset, table, column)]

    return [get_asset_metadata, get_dependencies, get_downstream_usage]
