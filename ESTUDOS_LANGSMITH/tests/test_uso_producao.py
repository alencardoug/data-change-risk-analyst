"""As consultas de uso rodam num Postgres real; sem banco alcançável o teste é pulado, não aprovado."""

from __future__ import annotations

import importlib
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

COURSE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COURSE / "labs"))
sys.path.insert(0, str(COURSE.parent / "src"))


def _url_alcancavel() -> str | None:
    url = os.getenv("DATABASE_URL")
    if not url:
        return None
    host = url.split("@")[-1].split("/")[0].split(":")[0]
    # O teste grava e apaga linhas; só num banco local, a menos que alguém peça o contrário.
    if host not in {"localhost", "127.0.0.1", "postgres"} and os.getenv("DCRA_ALLOW_REMOTE_DB_TESTS") != "1":
        return None
    try:
        import psycopg

        with psycopg.connect(url, connect_timeout=2):
            return url
    except Exception:
        return None


@pytest.fixture
def banco():
    url = _url_alcancavel()
    if url is None:
        pytest.skip("DATABASE_URL ausente ou sem Postgres respondendo (docker compose up -d postgres).")
    from dcra.persistence.repository import PostgresRepository

    repo = PostgresRepository(url)
    repo.setup()
    yield url, repo
    import psycopg

    with psycopg.connect(url) as conn:
        conn.execute("DELETE FROM analysis_record WHERE id LIKE 'curso-18-%'")


def _registro(ident: str, *, risco: str | None, decisao: str | None, espera_s: int = 0):
    from dcra.domain.enums import Outcome, ReviewDecision, RiskCategory
    from dcra.domain.models import AnalysisRecord, ChangeRequest, ReviewAction, RiskAssessment

    pedido = datetime.now(UTC) - timedelta(seconds=espera_s + 5)
    cr = ChangeRequest(id=ident, raw_text="drop column orders.customer_legacy_id", submitted_by="curso",
                       submitted_at=pedido)
    acoes = ([ReviewAction(decision=ReviewDecision(decisao), reviewer="curso",
                           decided_at=pedido + timedelta(seconds=espera_s))] if decisao else [])
    return AnalysisRecord(
        id=ident, change_request=cr,
        risk_assessments=[RiskAssessment(category=RiskCategory(risco))] if risco else [],
        review_actions=acoes, reviewed=bool(acoes),
        outcome=Outcome.APPROVED if decisao == "APPROVE" else Outcome.AUTO_FINALIZED,
        final_recommendation_version=1, step_log=["curso"],
    )


def test_usage_queries_use_request_time_and_name_missing_risk(banco):
    url, repo = banco
    mod = importlib.import_module("18_uso_producao")
    repo.save(_registro("curso-18-low", risco="LOW", decisao=None))
    repo.save(_registro("curso-18-medium", risco="MEDIUM", decisao="APPROVE", espera_s=300))
    repo.save(_registro("curso-18-sem-risco", risco=None, decisao=None))
    r = mod.executar(url, dias=1)
    hoje = datetime.now(UTC).date()
    assert any(row["dia"] == hoje and row["casos"] >= 3 for row in r["casos_por_dia"])
    riscos = {row["risco"]: row["casos"] for row in r["risco_final"]}
    assert riscos.get("SEM_AVALIACAO", 0) >= 1 and riscos.get("MEDIUM", 0) >= 1 and riscos.get("LOW", 0) >= 1
    desfechos = {(row["outcome"], row["reviewed"]): row["casos"] for row in r["desfechos"]}
    assert desfechos.get(("APPROVED", True), 0) >= 1 and desfechos.get(("AUTO_FINALIZED", False), 0) >= 2
    espera = r["espera_humana_s"][0]
    # Medida a partir do pedido, não do created_at do registro: positiva e da ordem dos 300 s inseridos.
    assert espera["n"] >= 1 and float(espera["p50_s"]) > 0 and float(espera["max_s"]) >= 299
    por_revisao = {row["reviewed"]: row for row in r["tempo_ate_concluir_s"]}
    assert por_revisao[True]["n"] >= 1 and por_revisao[False]["n"] >= 2
    inicio_fim = r["iniciados_vs_concluidos"][0]
    assert isinstance(inicio_fim["iniciados"], int) and inicio_fim["concluidos"] >= 3


def test_offline_mode_only_prints_the_queries(capsys):
    mod = importlib.import_module("18_uso_producao")
    sys.argv = ["18_uso_producao.py", "--dias", "7"]
    mod.main()
    out = capsys.readouterr().out
    assert "make_interval(days => 7)" in out and "%(dias)s" not in out
    assert out.count("analysis_record") >= len(mod.CONSULTAS) - 1 and "Nada foi consultado" in out
