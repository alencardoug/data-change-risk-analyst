"""``PostgresInspector`` — reads column metadata and lineage from a real database.

Column type / nullability / PK / UNIQUE come from ``information_schema``;
inbound foreign keys and view dependencies from ``pg_catalog`` /
``information_schema.view_column_usage``. Downstream *usage* is not a database
fact, so it is delegated to the simulated catalog (``DatasetInspector``).

Schema under test: ``deploy/warehouse_schema.sql`` (the real counterpart of
``dcra.evidence.dataset``). If that schema was never loaded (no ``orders``
table), every call transparently falls back to the simulated catalog so a
half-configured environment still behaves like the pure-dataset default.
"""

from __future__ import annotations

from dcra.domain.enums import EvidenceKind, EvidenceStatus
from dcra.domain.models import EvidenceItem
from dcra.evidence.dataset import (
    SOURCE_CATALOG,
    SOURCE_LINEAGE,
    Dataset,
)
from dcra.evidence.inspector import DatasetInspector

_SENTINEL_TABLE = "public.orders"  # presence ⇒ warehouse schema is loaded


def _split(table: str) -> tuple[str, str]:
    if "." in table:
        schema, _, name = table.partition(".")
        return schema, name
    return "public", table


class PostgresInspector:
    def __init__(self, url: str, dataset: Dataset | None = None) -> None:
        self._url = url
        self._fallback = DatasetInspector(dataset) if dataset is not None else None
        self._ready: bool | None = None

    # -- connection -------------------------------------------------------------

    def _connect(self):
        import psycopg

        return psycopg.connect(self._url)

    def _warehouse_ready(self) -> bool:
        if self._ready is None:
            try:
                with self._connect() as conn, conn.cursor() as cur:
                    cur.execute("SELECT to_regclass(%s)", (_SENTINEL_TABLE,))
                    self._ready = cur.fetchone()[0] is not None
            except Exception:
                self._ready = False
        return self._ready

    # -- Inspector protocol ---------------------------------------------------

    def asset_metadata(self, table: str, column: str | None) -> list[EvidenceItem]:
        if not self._warehouse_ready():
            return self._fb("asset_metadata", table, column)

        schema, name = _split(table)
        key = f"{table}.{column}" if column else table
        with self._connect() as conn, conn.cursor() as cur:
            if column is None:
                cur.execute("SELECT to_regclass(%s)", (f"{schema}.{name}",))
                if cur.fetchone()[0] is None:
                    return [_not_found(EvidenceKind.ASSET_METADATA, key)]
                payload = {"table": name, "column": None}
                return [_obtained(EvidenceKind.ASSET_METADATA, key, SOURCE_CATALOG, payload)]

            cur.execute(
                """
                SELECT data_type, is_nullable = 'YES'
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s AND column_name = %s
                """,
                (schema, name, column),
            )
            row = cur.fetchone()
            if row is None:
                return [_not_found(EvidenceKind.ASSET_METADATA, key)]
            data_type, is_nullable = row

            in_pk = _in_constraint(cur, schema, name, column, "PRIMARY KEY")
            in_uq = _in_constraint(cur, schema, name, column, "UNIQUE")

            cur.execute(
                "SELECT reltuples::bigint FROM pg_class WHERE oid = to_regclass(%s)",
                (f"{schema}.{name}",),
            )
            est = cur.fetchone()
            row_estimate = est[0] if est and est[0] is not None and est[0] >= 0 else None

        return [
            _obtained(
                EvidenceKind.ASSET_METADATA,
                key,
                SOURCE_CATALOG,
                {
                    "table": name,
                    "column": column,
                    "data_type": data_type,
                    "is_nullable": bool(is_nullable),
                    "in_primary_key": in_pk,
                    "in_unique_constraint": in_uq,
                    "row_estimate": row_estimate,
                },
            )
        ]

    def dependencies(self, table: str, column: str) -> list[EvidenceItem]:
        if not self._warehouse_ready():
            return self._fb("dependencies", table, column)

        schema, name = _split(table)
        items: list[EvidenceItem] = []
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT view_schema, view_name
                FROM information_schema.view_column_usage
                WHERE table_schema = %s AND table_name = %s AND column_name = %s
                ORDER BY view_schema, view_name
                """,
                (schema, name, column),
            )
            for vs, vn in cur.fetchall():
                dep = f"{vs}.{vn}"
                items.append(
                    _obtained(
                        EvidenceKind.DEPENDENCY,
                        dep,
                        SOURCE_LINEAGE,
                        {
                            "dependent": dep,
                            "dependent_type": "view",
                            "columns_referenced": [column],
                        },
                    )
                )

            cur.execute(
                """
                SELECT con.conname
                FROM pg_constraint con
                WHERE con.contype = 'f'
                  AND con.confrelid = to_regclass(%s)
                  AND EXISTS (
                      SELECT 1
                      FROM unnest(con.confkey) AS k(attnum)
                      JOIN pg_attribute att
                        ON att.attrelid = con.confrelid AND att.attnum = k.attnum
                      WHERE att.attname = %s
                  )
                ORDER BY con.conname
                """,
                (f"{schema}.{name}", column),
            )
            for (conname,) in cur.fetchall():
                items.append(
                    _obtained(
                        EvidenceKind.DEPENDENCY,
                        conname,
                        SOURCE_LINEAGE,
                        {
                            "dependent": conname,
                            "dependent_type": "foreign_key",
                            "columns_referenced": [column],
                        },
                    )
                )
        return items

    def downstream_usage(self, table: str, column: str) -> list[EvidenceItem]:
        # Not a database fact — always the simulated catalog.
        if self._fallback is None:
            return []
        return self._fallback.downstream_usage(table, column)

    # -- helpers ------------------------------------------------------------

    def _fb(self, method: str, *args) -> list[EvidenceItem]:
        if self._fallback is None:
            return []
        return getattr(self._fallback, method)(*args)


def _in_constraint(cur, schema: str, table: str, column: str, ctype: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON kcu.constraint_schema = tc.constraint_schema
         AND kcu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = %s
          AND tc.table_schema = %s AND tc.table_name = %s
          AND kcu.column_name = %s
        LIMIT 1
        """,
        (ctype, schema, table, column),
    )
    return cur.fetchone() is not None


def _obtained(kind: EvidenceKind, key: str, source: str, payload: dict) -> EvidenceItem:
    return EvidenceItem(
        kind=kind, key=key, status=EvidenceStatus.OBTAINED, source=source, payload=payload
    )


def _not_found(kind: EvidenceKind, key: str) -> EvidenceItem:
    return EvidenceItem(
        kind=kind,
        key=key,
        status=EvidenceStatus.UNAVAILABLE,
        source=SOURCE_CATALOG,
        payload={"reason": "not_found"},
    )
