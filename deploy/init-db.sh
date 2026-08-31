#!/usr/bin/env bash
# One-time (safe to re-run) production database setup against Neon:
#   1. creates the `analysis_record` table (PostgresRepository.setup -> schema.sql)
#   2. creates the LangGraph checkpoint tables (PostgresSaver.setup)
#   3. loads the simulated warehouse (deploy/warehouse_schema.sql): the `orders`
#      table + `reporting` views the tool introspects at analysis time
#
# Runs locally against whatever DATABASE_URL points at — it does NOT run inside
# Cloud Run and does not touch your local docker-compose database.
#
# Required: DATABASE_URL (Neon, ?sslmode=require). OPENAI_API_KEY is not needed
# here — no model is called.
set -euo pipefail

if [ -z "${DATABASE_URL:-}" ]; then
  echo "export DATABASE_URL first (Neon connection string, ?sslmode=require)" >&2
  exit 1
fi

cd "$(dirname "$0")/.."

uv run python - <<'PY'
import os
import pathlib

import psycopg

from dcra.persistence.checkpointer import make_checkpointer
from dcra.persistence.repository import PostgresRepository

url = os.environ["DATABASE_URL"]

PostgresRepository(url).setup()
print("analysis_record: ready")

saver = make_checkpointer(url)  # runs PostgresSaver.setup()
print("checkpoint tables: ready")
saver.conn.close()

sql = pathlib.Path("deploy/warehouse_schema.sql").read_text()
with psycopg.connect(url) as conn:  # no placeholders -> multi-statement is fine
    conn.execute(sql)
    conn.commit()
print("warehouse (orders + reporting views): ready")
PY

echo "Database initialised against DATABASE_URL."
