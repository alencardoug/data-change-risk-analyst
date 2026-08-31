"""Dependency bundle for the graph, so tests can inject deterministic fakes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from dcra.config import Settings
from dcra.domain.models import EvidenceItem, Recommendation, StructuredChange
from dcra.evidence.dataset import Dataset, default_dataset
from dcra.evidence.inspector import DatasetInspector, Inspector


class Repository(Protocol):
    def setup(self) -> None: ...
    def save(self, record: Any) -> None: ...
    def get(self, record_id: str) -> Any | None: ...


InterpretFn = Callable[[str], StructuredChange]
RecommendFn = Callable[..., Recommendation]  # keyword args: change, evidence, risk, note, version
InvestigateFn = Callable[..., list[EvidenceItem]]  # keyword args: change, gap_note
UsageReaderFn = Callable[[str, str], list[EvidenceItem]]  # (table, column) -> downstream usage


@dataclass
class GraphDeps:
    interpret_fn: InterpretFn
    recommend_fn: RecommendFn
    investigate_fn: InvestigateFn
    dataset: Dataset
    repository: Repository | None = None
    revision_limit: int = 2
    # V1 (ADR-020): the downstream-usage read can be swapped for an MCP-backed reader.
    # None ⇒ the graph uses the local `read_downstream_usage(dataset, ...)`.
    usage_reader: UsageReaderFn | None = None
    # Evidence source for collect_asset/collect_deps/collect_usage. None ⇒ the simulated
    # catalog (`DatasetInspector` over `dataset`); production wires a `PostgresInspector`.
    inspector: Inspector | None = None

    def inspect(self) -> Inspector:
        return self.inspector or DatasetInspector(self.dataset)


def production_deps(settings: Settings, dataset: Dataset | None = None) -> GraphDeps:
    """Wire the real LLM-backed callables and the Postgres repository."""
    from dcra.evidence.tools import make_evidence_tools
    from dcra.llm.factory import (
        build_chat_model,
        draft_recommendation,
        interpret,
        run_investigation,
    )
    from dcra.persistence.repository import PostgresRepository

    model = build_chat_model(settings)
    ds = dataset or default_dataset()
    tools = make_evidence_tools(ds)

    usage_reader = None
    if settings.usage_via_mcp:
        from dcra.mcp.client import read_downstream_usage_via_mcp

        usage_reader = read_downstream_usage_via_mcp

    inspector = None
    if settings.database_url:
        from dcra.evidence.warehouse import PostgresInspector

        # Reads real column metadata + lineage from the DB; usage stays synthetic.
        # Falls back to `ds` when the warehouse schema (deploy/warehouse_schema.sql)
        # is not loaded, so the pure-dataset behaviour is preserved otherwise.
        inspector = PostgresInspector(settings.database_url, ds)

    return GraphDeps(
        interpret_fn=lambda raw: interpret(model, raw),
        recommend_fn=lambda **kw: draft_recommendation(model, **kw),
        investigate_fn=lambda **kw: run_investigation(model, tools=tools, **kw),
        dataset=ds,
        repository=PostgresRepository(settings.database_url) if settings.database_url else None,
        revision_limit=settings.revision_limit,
        usage_reader=usage_reader,
        inspector=inspector,
    )
