"""Shared test fixtures. Deterministic tiers use fakes + MemorySaver — no LLM, no DB."""

from __future__ import annotations

import os
import re

import pytest

from dcra.domain.enums import Confidence, Disposition, Operation
from dcra.domain.models import (
    ChangeRequest,
    EvidenceItem,
    InterpretationError,
    Recommendation,
    StructuredChange,
)
from dcra.evidence.dataset import default_dataset
from dcra.graph.build import build_graph
from dcra.graph.deps import GraphDeps

# --------------------------------------------------------------------------- fakes
_DROP_RE = re.compile(r"drop column\s+(\w+)\.(\w+)", re.I)
_REMOVE_RE = re.compile(r"remove (?:the )?column\s+(\w+)\s+from\s+(?:the\s+)?(\w+)", re.I)
_ALTER_RE = re.compile(r"alter column\s+(\w+)\.(\w+)", re.I)
_INDEX_RE = re.compile(r"add index on\s+(\w+)\s*\(([^)]+)\)", re.I)


def keyword_interpret(raw: str) -> StructuredChange:
    """Tiny deterministic stand-in for the interpretation LLM call."""
    if m := _DROP_RE.search(raw):
        return StructuredChange(operation=Operation.DROP_COLUMN, target_table=m.group(1),
                                target_column=m.group(2))
    if m := _REMOVE_RE.search(raw):
        return StructuredChange(operation=Operation.DROP_COLUMN, target_table=m.group(2),
                                target_column=m.group(1))
    if m := _ALTER_RE.search(raw):
        return StructuredChange(operation=Operation.ALTER_COLUMN, target_table=m.group(1),
                                target_column=m.group(2), alter_detail="type/nullability change")
    if m := _INDEX_RE.search(raw):
        cols = [c.strip() for c in m.group(2).split(",") if c.strip()]
        return StructuredChange(operation=Operation.ADD_INDEX, target_table=m.group(1),
                                index_columns=cols)
    raise InterpretationError(f"not a recognised data change: {raw!r}")


def fake_recommend(disposition: Disposition = Disposition.PROCEED):
    def _rec(*, change, evidence, risk, note, version) -> Recommendation:
        reduced = any(e.status.value == "UNAVAILABLE" for e in evidence)
        return Recommendation(
            version=version,
            disposition=disposition,
            rationale=f"Deterministic test recommendation for {risk.category.value} risk.",
            mitigations=["mitigation"] if disposition == Disposition.PROCEED_WITH_MITIGATION else [],
            confidence=Confidence.REDUCED if reduced else Confidence.NORMAL,
            prompted_by_note=note,
        )

    return _rec


def fake_investigate(items: list[EvidenceItem] | None = None):
    def _inv(*, change, gap_note) -> list[EvidenceItem]:
        return list(items or [])

    return _inv


class InMemoryRepository:
    def __init__(self) -> None:
        self.saved: dict[str, object] = {}

    def setup(self) -> None:  # noqa: D401
        pass

    def save(self, record) -> None:
        self.saved[record.id] = record

    def get(self, record_id: str):
        return self.saved.get(record_id)


# ------------------------------------------------------------------------- builders
@pytest.fixture
def dataset():
    return default_dataset


@pytest.fixture
def make_deps():
    def _make(
        *,
        interpret_fn=keyword_interpret,
        recommend_fn=None,
        investigate_fn=None,
        disabled_sources: set[str] | None = None,
        repository=None,
        revision_limit: int = 2,
    ) -> GraphDeps:
        return GraphDeps(
            interpret_fn=interpret_fn,
            recommend_fn=recommend_fn or fake_recommend(),
            investigate_fn=investigate_fn or fake_investigate(),
            dataset=default_dataset(disabled_sources=disabled_sources),
            repository=repository,
            revision_limit=revision_limit,
        )

    return _make


@pytest.fixture
def graph_for():
    def _build(deps: GraphDeps):
        return build_graph(deps)

    return _build


@pytest.fixture
def change_request():
    def _cr(text: str, by: str = "data.engineer") -> ChangeRequest:
        return ChangeRequest(raw_text=text, submitted_by=by)

    return _cr


@pytest.fixture(autouse=True)
def _no_tracing(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "false")


def requires_llm():
    return pytest.mark.skipif(
        os.getenv("RUN_LLM_TESTS") != "1", reason="set RUN_LLM_TESTS=1 to run LLM tests"
    )
