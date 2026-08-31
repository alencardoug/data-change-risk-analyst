"""The evidence source seam.

An ``Inspector`` answers the three read-only questions the collector nodes ask
about a proposed change's target column. Two implementations:

* ``DatasetInspector`` — the in-repo simulated catalog (``dcra.evidence.dataset``).
  Deterministic, no I/O; this is what every test uses.
* ``PostgresInspector`` (``dcra.evidence.warehouse``) — reads real column
  metadata and dependencies from ``information_schema`` / ``pg_catalog``.

Only ``production_deps`` picks the Postgres one; ``GraphDeps.inspect()`` falls
back to ``DatasetInspector`` otherwise.
"""

from __future__ import annotations

from typing import Protocol

from dcra.domain.models import EvidenceItem
from dcra.evidence.dataset import Dataset
from dcra.evidence.tools import (
    read_asset_metadata,
    read_dependencies,
    read_downstream_usage,
)


class Inspector(Protocol):
    def asset_metadata(self, table: str, column: str | None) -> list[EvidenceItem]: ...

    def dependencies(self, table: str, column: str) -> list[EvidenceItem]: ...

    def downstream_usage(self, table: str, column: str) -> list[EvidenceItem]: ...


class DatasetInspector:
    """Reads the simulated catalog. The default everywhere except production."""

    def __init__(self, dataset: Dataset) -> None:
        self._ds = dataset

    def asset_metadata(self, table: str, column: str | None) -> list[EvidenceItem]:
        return read_asset_metadata(self._ds, table, column)

    def dependencies(self, table: str, column: str) -> list[EvidenceItem]:
        return read_dependencies(self._ds, table, column)

    def downstream_usage(self, table: str, column: str) -> list[EvidenceItem]:
        return read_downstream_usage(self._ds, table, column)
