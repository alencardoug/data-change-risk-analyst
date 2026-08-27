"""AnalysisRecord persistence via psycopg (parametrized SQL). DB-gated in tests."""

from __future__ import annotations

import json
from pathlib import Path

from dcra.domain.models import AnalysisRecord

_SCHEMA = Path(__file__).with_name("schema.sql")

_UPSERT = """
INSERT INTO analysis_record (
    id, change_request, structured_change, evidence, risk_assessments,
    recommendations, review_actions, reviewed, outcome,
    final_recommendation_version, step_log, created_at, finalized_at
) VALUES (
    %(id)s, %(change_request)s, %(structured_change)s, %(evidence)s, %(risk_assessments)s,
    %(recommendations)s, %(review_actions)s, %(reviewed)s, %(outcome)s,
    %(final_recommendation_version)s, %(step_log)s, %(created_at)s, %(finalized_at)s
)
ON CONFLICT (id) DO UPDATE SET
    change_request = EXCLUDED.change_request,
    structured_change = EXCLUDED.structured_change,
    evidence = EXCLUDED.evidence,
    risk_assessments = EXCLUDED.risk_assessments,
    recommendations = EXCLUDED.recommendations,
    review_actions = EXCLUDED.review_actions,
    reviewed = EXCLUDED.reviewed,
    outcome = EXCLUDED.outcome,
    final_recommendation_version = EXCLUDED.final_recommendation_version,
    step_log = EXCLUDED.step_log,
    finalized_at = EXCLUDED.finalized_at;
"""


class PostgresRepository:
    def __init__(self, database_url: str) -> None:
        self._url = database_url

    def _connect(self):
        import psycopg

        return psycopg.connect(self._url)

    def setup(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(_SCHEMA.read_text())
            conn.commit()

    def save(self, record: AnalysisRecord) -> None:
        d = record.model_dump(mode="json")
        params = {
            "id": d["id"],
            "change_request": json.dumps(d["change_request"]),
            "structured_change": json.dumps(d["structured_change"]),
            "evidence": json.dumps(d["evidence"]),
            "risk_assessments": json.dumps(d["risk_assessments"]),
            "recommendations": json.dumps(d["recommendations"]),
            "review_actions": json.dumps(d["review_actions"]),
            "reviewed": d["reviewed"],
            "outcome": d["outcome"],
            "final_recommendation_version": d["final_recommendation_version"],
            "step_log": json.dumps(d["step_log"]),
            "created_at": d["created_at"],
            "finalized_at": d["finalized_at"],
        }
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(_UPSERT, params)
            conn.commit()

    def get(self, record_id: str) -> AnalysisRecord | None:
        cols = [
            "id", "change_request", "structured_change", "evidence", "risk_assessments",
            "recommendations", "review_actions", "reviewed", "outcome",
            "final_recommendation_version", "step_log", "created_at", "finalized_at",
        ]
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"SELECT {', '.join(cols)} FROM analysis_record WHERE id = %s", (record_id,)
            )
            row = cur.fetchone()
        if row is None:
            return None
        data = dict(zip(cols, row, strict=True))
        for k in ("created_at", "finalized_at"):
            if data[k] is not None:
                data[k] = data[k].isoformat()
        return AnalysisRecord.model_validate(data)
