"""PostgresInspector reads real column metadata + lineage and feeds the risk rules.

DB-gated: needs DATABASE_URL + a reachable Postgres. Loads deploy/warehouse_schema.sql
into that database, then checks the canonical scenarios still land on the expected
risk category — the same ones the simulated `default_dataset()` produces.
"""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

from dcra.domain.enums import Operation, RiskCategory
from dcra.domain.models import StructuredChange
from dcra.evidence.dataset import default_dataset
from dcra.evidence.warehouse import PostgresInspector
from dcra.rules import risk as risk_rules
from tests.conftest import reachable_db_url

_DB = reachable_db_url()
pytestmark = pytest.mark.skipif(not _DB, reason="needs a reachable Postgres (docker compose up -d)")

_SCHEMA_SQL = Path(__file__).parents[2] / "deploy" / "warehouse_schema.sql"


@pytest.fixture(scope="module")
def inspector() -> PostgresInspector:
    with psycopg.connect(_DB) as conn:
        conn.execute(_SCHEMA_SQL.read_text())
        conn.commit()
    return PostgresInspector(_DB, default_dataset())


def _category(insp: PostgresInspector, op: Operation, table: str,
              column: str | None = None, index_columns: list[str] | None = None) -> RiskCategory:
    sc = StructuredChange(
        operation=op, target_table=table, target_column=column,
        index_columns=index_columns or [], confidence=0.9,
    )
    col = column or (index_columns[0] if index_columns else "")
    ev = insp.asset_metadata(table, col or None)
    if col:
        ev += insp.dependencies(table, col)
        ev += insp.downstream_usage(table, col)
    return risk_rules.assess(sc, ev).category


@pytest.mark.parametrize(
    "op,table,column,index_columns,expected",
    [
        (Operation.DROP_COLUMN, "orders", "customer_legacy_id", None, RiskCategory.MEDIUM),
        (Operation.DROP_COLUMN, "orders", "notes_internal", None, RiskCategory.LOW),
        (Operation.DROP_COLUMN, "orders", "status", None, RiskCategory.MEDIUM),
        (Operation.DROP_COLUMN, "orders", "id", None, RiskCategory.HIGH),
        (Operation.ALTER_COLUMN, "orders", "status", None, RiskCategory.MEDIUM),
        (Operation.ADD_INDEX, "orders", None, ["customer_id"], RiskCategory.LOW),
        (Operation.DROP_COLUMN, "orders", "legacy_region", None, RiskCategory.HIGH),
        (Operation.DROP_COLUMN, "ghost_table", "foo", None, RiskCategory.HIGH),
    ],
)
def test_scenarios_match_expected_category(
    inspector, op, table, column, index_columns, expected
):
    assert _category(inspector, op, table, column, index_columns) is expected


def test_metadata_reports_pk_and_type(inspector):
    (item,) = inspector.asset_metadata("orders", "id")
    assert item.status.value == "OBTAINED"
    assert item.payload["in_primary_key"] is True
    assert item.payload["data_type"] == "bigint"
    assert item.payload["row_estimate"] and item.payload["row_estimate"] > 0


def test_inbound_fk_is_a_dependency(inspector):
    deps = inspector.dependencies("orders", "id")
    fks = [d for d in deps if (d.payload or {}).get("dependent_type") == "foreign_key"]
    assert any(d.payload["dependent"] == "fk_order_items_order" for d in fks)


def test_views_are_dependencies(inspector):
    deps = inspector.dependencies("orders", "customer_legacy_id")
    views = {d.payload["dependent"] for d in deps
             if (d.payload or {}).get("dependent_type") == "view"}
    assert "reporting.v_legacy_bridge" in views
    assert "reporting.v_customer_orders" in views


def test_unknown_table_falls_back_to_not_found(inspector):
    (item,) = inspector.asset_metadata("ghost_table", "foo")
    assert item.status.value == "UNAVAILABLE"
    assert (item.payload or {}).get("reason") == "not_found"
