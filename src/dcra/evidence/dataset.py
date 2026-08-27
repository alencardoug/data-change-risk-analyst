"""Simulated structured evidence source. Fully in-repo; no external systems (Constitution scope).

Granularity is table.column. ``disabled_sources`` simulates an unavailable evidence source
(FR-024). ``orders.legacy_region`` is intentionally absent to exercise FR-020.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SOURCE_CATALOG = "catalog"
SOURCE_LINEAGE = "lineage"
SOURCE_USAGE = "usage"


@dataclass
class ColumnFacts:
    data_type: str
    is_nullable: bool
    in_primary_key: bool = False
    in_unique_constraint: bool = False
    row_estimate: int | None = None
    # dependents referencing this column
    dependencies: list[dict] = field(default_factory=list)
    # downstream consumers reading this column
    usage: list[dict] = field(default_factory=list)


@dataclass
class Dataset:
    columns: dict[str, ColumnFacts]
    disabled_sources: set[str] = field(default_factory=set)

    def get(self, table: str, column: str | None) -> ColumnFacts | None:
        if column is None:
            # table-level lookup: return any column's facts is meaningless; expose a marker
            return self.columns.get(f"{table}.*")
        return self.columns.get(f"{table}.{column}")

    def source_disabled(self, source: str) -> bool:
        return source in self.disabled_sources


def default_dataset(disabled_sources: set[str] | None = None) -> Dataset:
    cols: dict[str, ColumnFacts] = {
        # HIGH-ish: referenced by two views, has FK, still read recently
        "orders.customer_legacy_id": ColumnFacts(
            data_type="varchar",
            is_nullable=True,
            row_estimate=1_800_000,
            dependencies=[
                {"dependent": "reporting.v_customer_orders", "dependent_type": "view",
                 "columns_referenced": ["customer_legacy_id"]},
                {"dependent": "reporting.v_legacy_bridge", "dependent_type": "view",
                 "columns_referenced": ["customer_legacy_id"]},
            ],
            usage=[
                {"consumer": "cs_lookup", "consumer_type": "service",
                 "last_read_at": "2026-08-19T14:11:00Z", "reads_per_day": 4},
            ],
        ),
        # LOW: no dependents, not read in a long time
        "orders.notes_internal": ColumnFacts(
            data_type="text",
            is_nullable=True,
            row_estimate=1_800_000,
            dependencies=[],
            usage=[],
        ),
        # MEDIUM: one view, not read recently
        "orders.status": ColumnFacts(
            data_type="varchar",
            is_nullable=False,
            row_estimate=1_800_000,
            dependencies=[
                {"dependent": "reporting.v_open_orders", "dependent_type": "view",
                 "columns_referenced": ["status"]},
            ],
            usage=[
                {"consumer": "ops_dashboard", "consumer_type": "dashboard",
                 "last_read_at": "2026-05-01T00:00:00Z", "reads_per_day": 0},
            ],
        ),
        # HIGH: primary key column
        "orders.id": ColumnFacts(
            data_type="bigint",
            is_nullable=False,
            in_primary_key=True,
            row_estimate=1_800_000,
            dependencies=[
                {"dependent": "fk_order_items_order", "dependent_type": "foreign_key",
                 "columns_referenced": ["id"]},
            ],
            usage=[
                {"consumer": "warehouse_sync", "consumer_type": "job",
                 "last_read_at": "2026-08-27T01:00:00Z", "reads_per_day": 12},
            ],
        ),
        # for ADD_INDEX scenarios (index target column, low blast radius)
        "orders.customer_id": ColumnFacts(
            data_type="bigint",
            is_nullable=False,
            row_estimate=1_800_000,
            dependencies=[],
            usage=[
                {"consumer": "ops_dashboard", "consumer_type": "dashboard",
                 "last_read_at": "2026-08-27T09:00:00Z", "reads_per_day": 90},
            ],
        ),
    }
    return Dataset(columns=cols, disabled_sources=set(disabled_sources or set()))
