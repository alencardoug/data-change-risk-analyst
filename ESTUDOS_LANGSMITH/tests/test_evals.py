"""A suíte pytest de avaliação reproduz o lab 06 e reprova a mutação; tudo sem rede."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

COURSE = Path(__file__).resolve().parents[1]
ROOT = COURSE.parent
sys.path.insert(0, str(COURSE / "labs"))

SITECUSTOMIZE = (
    "import os, socket\n"
    "def blocked(*args, **kwargs):\n"
    "    with open(os.environ['DCRA_LAB_NETWORK_MARKER'], 'a') as f:\n"
    "        f.write('network attempt blocked\\n')\n"
    "    raise RuntimeError('Network disabled by test')\n"
    "socket.socket.connect = blocked\n"
    "socket.socket.connect_ex = blocked\n"
    "socket.create_connection = blocked\n"
    "socket.getaddrinfo = blocked\n"
)


def run_suite(tmp_path: Path, *extra: str) -> tuple[int, dict | None]:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir(exist_ok=True)
    (sandbox / "sitecustomize.py").write_text(SITECUSTOMIZE)
    marker = sandbox / "network-attempts.txt"
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTEST_", "LANGSMITH_", "LANGCHAIN_"))}
    env |= {"PYTHONPATH": str(sandbox), "DCRA_LAB_NETWORK_MARKER": str(marker),
            "DCRA_EVALS_REPORT_DIR": str(tmp_path), "LANGSMITH_API_KEY": "chave-sintetica-para-teste-local"}
    env.pop("DCRA_EVALS_REMOTE", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(COURSE / "evals"), "-q", "-p", "no:cacheprovider", *extra],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120, check=False,
    )
    assert not marker.exists(), f"A suíte tentou usar a rede:\n{result.stdout}\n{result.stderr}"
    reports = list(tmp_path.glob("evals-*.json"))
    return result.returncode, json.loads(reports[0].read_text()) if reports else None


@pytest.mark.parametrize("variant,exit_code", [("baseline", 0), ("bug", 1)])
def test_pytest_suite_matches_lab_06_and_gates_the_mutation(tmp_path, variant, exit_code):
    from _common import configure, read_cases

    configure(Namespace(send=False, project="teste-local"))
    expected = importlib.import_module("06_evaluate").evaluate_local(read_cases(), variant)
    code, report = run_suite(tmp_path, "--variant", variant)
    assert code == exit_code
    assert report is not None and report["variant"] == variant and report["complete"] and not report["remote"]
    assert report["n"] == 16 and report["metrics"] == expected["metrics"]
    assert report["high_risk_recall"] == expected["high_risk_recall"]
    assert sorted(row["case_id"] for row in report["rows"]) == sorted(case["id"] for case in read_cases())


def test_selecting_one_case_does_not_pass_the_gate(tmp_path):
    # Exatamente o comando que um aluno digitaria: o caso passa, mas a sessão termina em 1 por incompletude.
    code, report = run_suite(tmp_path, "-k", "c01")
    assert code == 1
    assert report is not None and report["n"] == 1 and report["complete"] is False
    assert report["parcial"] is False and report["exit_status"] == 1
    assert report["policy"]["exige_conjunto_completo"] is True


def test_partial_flag_declares_investigation_and_keeps_the_report_marked(tmp_path):
    code, report = run_suite(tmp_path, "-k", "c01", "--parcial")
    assert code == 0
    assert report is not None and report["n"] == 1
    assert report["complete"] is False and report["parcial"] is True


def test_stale_report_is_removed_before_a_run_that_evaluates_nothing(tmp_path):
    stale = tmp_path / "evals-baseline.json"
    stale.write_text('{"variant": "baseline", "complete": true, "n": 16}')
    code, report = run_suite(tmp_path, "--collect-only")
    assert code == 0 and report is None and not stale.exists()


def test_manifest_covers_the_evaluation_suite_itself(tmp_path):
    _, report = run_suite(tmp_path)
    hashed = set(report["manifest"]["file_sha256"])
    assert {"ESTUDOS_LANGSMITH/evals/_suite.py", "ESTUDOS_LANGSMITH/evals/conftest.py",
            "ESTUDOS_LANGSMITH/evals/test_contratos_dcra.py"} <= hashed
