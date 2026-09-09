"""Verificações do material executável; rede bloqueada e nenhum provedor real."""

from __future__ import annotations

import importlib
import socket
import sys
from argparse import Namespace
from decimal import Decimal
from pathlib import Path

import pytest

LABS = Path(__file__).resolve().parents[1] / "labs"
sys.path.insert(0, str(LABS))


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("LANGSMITH_API_KEY", "chave-sintetica-para-teste-local")

    def blocked(*args, **kwargs):
        raise AssertionError("O teste local tentou abrir uma conexão de rede.")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def test_baseline_and_regression_on_independent_references():
    from _common import configure, read_cases

    configure(Namespace(send=False, project="teste-local"))
    module = importlib.import_module("06_evaluate")
    cases = read_cases()
    baseline = module.evaluate_local(cases, "baseline")
    bug = module.evaluate_local(cases, "bug")
    assert baseline["n"] == 16
    assert all(value == 1 for value in baseline["metrics"].values())
    assert bug["metrics"]["risk_correct"] == 13 / 16
    assert baseline["high_risk_recall"] == 1
    assert bug["high_risk_recall"] == 0


@pytest.mark.parametrize("decision,missing,versions,risk_passes", [
    ("APPROVE", False, [1], 1), ("RETURN", False, [1, 2], 1), ("RETURN", True, [1, 2], 3),
])
def test_actual_graph_pause_and_review(decision, missing, versions, risk_passes):
    from _dcra import make_deps, review, summarize

    from dcra.domain.models import ChangeRequest
    from dcra.graph.build import build_graph, pending_interrupt, run

    graph = build_graph(make_deps())
    cr = ChangeRequest(raw_text="drop column orders.customer_legacy_id", submitted_by="teste")
    paused = run(graph, cr)
    assert pending_interrupt(paused) is not None
    state = review(graph.with_config(run_name="retomar"), cr.id, decision, evidence_missing=missing)
    result = summarize(state, cr.id)
    assert result["recommendation_versions"] == versions
    assert result["risk_passes"] == risk_passes
    assert result["awaiting_review"] == (decision == "RETURN")
    if decision == "RETURN":
        final = review(graph, cr.id, "APPROVE")
        assert final["outcome"] == "APPROVED"


def test_cost_cache_is_subset_and_budget_refuses_fourth_call():
    mod = importlib.import_module("09_costs")
    amount = mod.token_cost(1000, 200, 200)
    assert amount == Decimal("0.0033")
    budget = mod.Budget(Decimal("0.010"))
    assert [budget.reserve(amount) for _ in range(4)] == [True, True, True, False]
    with pytest.raises(ValueError):
        mod.token_cost(100, 20, 200)


def test_privacy_processors_change_trace_but_not_application_return():
    from langsmith import Client, tracing_context

    mod = importlib.import_module("10_privacy")
    roots = []
    original = {"email": "pessoa@example.com"}
    client = Client(api_key="chave-local-sintetica", auto_batch_tracing=False)
    with tracing_context(enabled="local", client=client):
        output = mod.contact(original, langsmith_extra={"on_end": roots.append})
    assert output == {"ack": "Recebido de pessoa@example.com"}
    assert original == {"email": "pessoa@example.com"}
    assert "pessoa@example.com" not in str(roots[0].inputs)
    assert "pessoa@example.com" not in str(roots[0].outputs)
    assert "EMAIL_REMOVIDO" in str(roots[0].inputs)


def test_nested_trace_has_metadata_and_no_model_spans():
    from langsmith import Client, traceable, tracing_context

    mod = importlib.import_module("01_trace_python")
    roots = []
    client = Client(api_key="chave-local-sintetica", auto_batch_tracing=False)
    with tracing_context(enabled="local", client=client, metadata={"thread_id": "caso-local"}):
        result = traceable(mod.order, name="pedido")(
            {"item": "risoto", "quantidade": 2}, langsmith_extra={"on_end": roots.append}
        )
    root = roots[0]
    assert result["total_reais"] == 36
    assert {r.name for r in root.child_runs} == {"consultar_cardapio", "calcular_total"}
    assert all(r.metadata["thread_id"] == "caso-local" for r in root.child_runs)
    assert all(r.run_type != "llm" for r in root.child_runs)


def test_rag_distinguishes_retrieval_and_generation_failure():
    mod = importlib.import_module("11_rag")
    good, retrieval, generation = [mod.score(mod.rag({"question": "prazo?", "mode": mode}))
                                   for mode in ["good", "bad_retrieval", "hallucination"]]
    assert good == {"retrieval_recall_at_1": 1, "answer_correct": 1, "supported_or_abstained": 1}
    assert retrieval == {"retrieval_recall_at_1": 0, "answer_correct": 0, "supported_or_abstained": 1}
    assert generation == {"retrieval_recall_at_1": 1, "answer_correct": 0, "supported_or_abstained": 0}


def test_context_is_lost_and_explicitly_restored():
    mod = importlib.import_module("14_context")
    result = mod.pipeline({"case_id": "caso-42"})
    assert result["lost"]["case_id"] == "sem-contexto"
    assert result["propagated"]["case_id"] == "caso-42"


def test_sdk_evaluator_adaptation_uses_reference_outputs():
    from datetime import UTC, datetime
    from uuid import uuid4

    from _evaluators import risk_correct
    from langsmith.evaluation import run_evaluator
    from langsmith.schemas import Example, Run

    run = Run(id=uuid4(), name="fake", run_type="chain", inputs={}, outputs={"risk": "LOW"},
              start_time=datetime.now(UTC), trace_id=uuid4())
    example = Example(id=uuid4(), dataset_id=uuid4(), inputs={}, outputs={"risk": "HIGH"},
                      created_at=datetime.now(UTC))
    result = run_evaluator(risk_correct).evaluate_run(run, example)
    assert result.score == 0
