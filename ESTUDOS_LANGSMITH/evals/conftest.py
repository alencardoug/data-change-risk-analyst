"""Suíte de avaliação pelo pytest: local por padrão; publica no LangSmith só com DCRA_EVALS_REMOTE=1."""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
COURSE = HERE.parent
ROOT = COURSE.parent
for path in (HERE, COURSE / "labs"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from _suite import CONTEXT, POLITICA, VARIANTS, Resultados  # noqa: E402

REMOTE = os.getenv("DCRA_EVALS_REMOTE", "").strip() == "1"

# `@pytest.mark.langsmith` decide na importação do módulo de teste se vai rastrear
# (lê LANGSMITH_TEST_TRACKING nesse momento). Por isso a escolha acontece aqui,
# antes da coleta, e não em uma fixture. O tracking de testes é um controle
# separado do tracing: um envia exemplos/feedback ao dataset, o outro envia runs.
if REMOTE:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
    from _common import credential_present

    if not credential_present("LANGSMITH_API_KEY"):
        raise pytest.UsageError("DCRA_EVALS_REMOTE=1 exige LANGSMITH_API_KEY no .env. Veja 03-preparacao.md.")
    os.environ["LANGSMITH_TEST_TRACKING"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ.setdefault("LANGSMITH_TEST_SUITE", "dcra-evals-contratos")
else:
    os.environ["LANGSMITH_TEST_TRACKING"] = "false"
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--variant", choices=VARIANTS, default=None,
                     help="baseline (padrão) ou bug: mutação HIGH→LOW que a suíte deve reprovar.")
    parser.addoption("--parcial", action="store_true", default=False,
                     help="Investigação de um subconjunto (-k): não reprova por incompletude. "
                          "Sem esta opção a suíte é um gate: menos que os 16 casos termina em exit 1.")


def _report_path(variant: str) -> Path:
    from _common import ARTIFACTS

    return Path(os.getenv("DCRA_EVALS_REPORT_DIR") or ARTIFACTS) / f"evals-{variant}.json"


def pytest_configure(config: pytest.Config) -> None:
    variant = config.getoption("variant", default=None) or os.getenv("DCRA_EVALS_VARIANT", "baseline")
    if variant not in VARIANTS:
        raise pytest.UsageError(f"Variante inválida: {variant!r}; use uma de {VARIANTS}.")
    CONTEXT["resultados"] = Resultados(variant)
    # Um relatório antigo no destino poderia passar por resultado desta execução; some antes de começar.
    _report_path(variant).unlink(missing_ok=True)
    if REMOTE:
        os.environ.setdefault("LANGSMITH_EXPERIMENT", f"dcra-evals-{variant}")
        os.environ.setdefault("LANGSMITH_EXPERIMENT_METADATA", json.dumps({
            "variant": variant, "evaluator_version": "contratos-v1", "runner": "pytest",
        }))


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    resultados: Resultados | None = CONTEXT.get("resultados")
    if not resultados or not resultados.rows:
        return
    from _common import manifest, read_cases
    from _evaluators import high_risk_recall

    expected = sorted(case["id"] for case in read_cases())
    evaluated = sorted(row["case_id"] for row in resultados.rows)
    complete = evaluated == expected
    parcial = session.config.getoption("parcial", default=False)
    if not complete and not parcial and int(exitstatus) == 0:
        # Modo gate: um subconjunto verde não aprova. Só --parcial declara que isto é investigação.
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.ensure_newline()
            reporter.write_line(
                f"GATE: avaliação incompleta ({len(evaluated)}/{len(expected)} casos); exit 1. "
                "Use --parcial para investigar um subconjunto sem gate.", red=True, bold=True)
    report = {
        "variant": resultados.variant, "remote": REMOTE,
        "exit_status": int(session.exitstatus),
        "n": len(resultados.rows), "complete": complete, "parcial": bool(parcial),
        "policy": POLITICA, "metrics": resultados.metrics(),
        "high_risk_recall": high_risk_recall(resultados.rows), "rows": resultados.rows,
        "manifest": manifest(),
    }
    path = _report_path(resultados.variant)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n")


@pytest.fixture(autouse=True)
def rede_bloqueada_no_modo_local(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem DCRA_EVALS_REMOTE=1, qualquer tentativa de conexão é um defeito da suíte."""
    if REMOTE:
        return

    def blocked(*args, **kwargs):
        raise AssertionError("A suíte local tentou abrir uma conexão de rede.")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
