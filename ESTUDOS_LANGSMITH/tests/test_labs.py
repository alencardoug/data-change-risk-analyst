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


def test_summary_evaluator_is_accepted_by_the_sdk_and_reports_the_set():
    from _evaluators import high_risk_recall_summary
    from langsmith.evaluation._runner import _normalize_summary_evaluator

    outputs = [{"risk": "LOW"}, {"risk": "LOW"}, {"risk": "MEDIUM"}]
    references = [{"risk": "HIGH"}, {"risk": "LOW"}, {"risk": "MEDIUM"}]
    assert high_risk_recall_summary(outputs, references) == {"key": "high_risk_recall", "score": 0.0}
    # Sem HIGH de referência não existe recall; ausência de nota, nunca zero.
    vazio = high_risk_recall_summary([{"risk": "LOW"}], [{"risk": "LOW"}])
    assert "score" not in vazio
    assert callable(_normalize_summary_evaluator(high_risk_recall_summary))


def test_aggregation_separates_denominators_and_respects_concurrency():
    mod = importlib.import_module("16_consultar_runs")
    import json

    path = Path(__file__).resolve().parents[1] / "dados" / "runs.jsonl"
    runs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    result = mod.analisar(runs, "collect_deps")
    d = result["denominadores"]
    # Quatro perguntas diferentes sobre "erro"; quatro respostas corretas e distintas.
    assert d["erro_por_pedido"] == round(1 / 3, 4)
    assert d["erro_por_run"] == round(3 / 14, 4)
    assert d["erro_por_tentativa_de_collect_deps"] == round(1 / 3, 4)
    assert d["pedidos_em_que_collect_deps_nunca_obteve_resposta"] == 0
    # Somar filhos concorrentes esconderia o trabalho próprio da raiz.
    tA = next(t for t in result["tempo_proprio"] if t["trace"] == "tA")
    assert tA["soma_ingenua_dos_filhos_ms"] == tA["raiz_ms"] == 1200.0
    assert tA["ocupacao_real_dos_filhos_ms"] == 1000.0
    assert tA["tempo_proprio_ms"] == 200.0
    assert result["latencia"]["collect_asset"]["n"] == 1
    assert mod.percentil([], 95) is None


def test_biased_judge_disagrees_on_two_known_cases_and_failure_is_not_a_grade():
    mod = importlib.import_module("08_judge")
    cases, fixture = mod.load_cases(), mod.load_biased_fixture()
    result = mod.summarize(mod.judge_fixture(cases, fixture), cases, fixture["notas_do_material"])
    assert (result["n_valid"], result["n_total"], result["agreement"]) == (6, 6, 4 / 6)
    assert [d["id"] for d in result["disagreements"]] == ["j02", "j05"]
    assert all(d["criteria"] == ["grounded"] and d["nota_do_material"] for d in result["disagreements"])
    # Os dois erros aceitam alegações sem sustentação: falsos positivos, o lado perigoso para um gate.
    assert result["per_criterion"]["grounded"] == {"agreement": 4 / 6, "false_positives": 2,
                                                   "false_negatives": 0}
    assert result["per_criterion"]["non_binding"]["agreement"] == 1.0
    # Uma falha do medidor sai do numerador e do denominador; não vira concordância nem zero.
    failed = mod.summarize(mod.judge_fixture(cases, fixture, fail_id="j04"), cases)
    assert (failed["n_valid"], failed["coverage"], failed["agreement"]) == (5, 5 / 6, 3 / 5)
    assert failed["judge_errors"] == [{"id": "j04", "error": "ValidationError (simulada)"}]
    assert [d["id"] for d in failed["disagreements"]] == ["j02", "j05"]


def _rows_locais(mod):
    import json

    return [mod.normalizar_local(json.loads(line))
            for line in (LABS.parent / "dados" / "runs.jsonl").read_text().splitlines() if line.strip()]


def test_export_uses_closed_window_and_is_idempotent(tmp_path):
    mod = importlib.import_module("17_exportar_runs")
    rows = _rows_locais(mod)
    desde, ate = (mod.instante(value) for value in mod.JANELA_LOCAL)
    first = mod.exportar(iter(rows), desde=desde, ate=ate, destino=tmp_path, maximo=100,
                         feedback=mod.feedback_local)
    assert first == {"truncado": False, "maximo": 100,
                     "runs": {"novos": 11, "ja_presentes": 0, "fora_da_janela": 3},
                     "feedback": {"novos": 3, "ja_presentes": 0}}
    before = mod.reconciliar(tmp_path)
    second = mod.exportar(iter(rows), desde=desde, ate=ate, destino=tmp_path, maximo=100,
                          feedback=mod.feedback_local)
    assert second["runs"] == {"novos": 0, "ja_presentes": 11, "fora_da_janela": 3}
    assert second["feedback"] == {"novos": 0, "ja_presentes": 3}
    after = mod.reconciliar(tmp_path)
    assert after == before and after["sha256"] == before["sha256"]
    assert after["ids_unicos"] and after["runs"] == 11 and after["traces"] == 2 and after["raizes"] == 2
    assert after["com_erro"] == 1 and after["feedback"] == 3 and after["feedback_sem_run_no_arquivo"] == 0
    # A janela é fechada à direita: tC começa às 10:09 e fica para a janela seguinte.
    later = mod.exportar(iter(rows), desde=ate, ate=mod.instante("2026-09-09T11:00:00Z"),
                         destino=tmp_path / "seguinte", maximo=100)
    assert later["runs"] == {"novos": 3, "ja_presentes": 0, "fora_da_janela": 11}


def test_export_keeps_free_text_out_unless_content_is_requested(tmp_path):
    mod = importlib.import_module("17_exportar_runs")
    rows = _rows_locais(mod)
    desde, ate = (mod.instante(value) for value in mod.JANELA_LOCAL)
    mod.exportar(iter(rows), desde=desde, ate=ate, destino=tmp_path / "min", maximo=100,
                 feedback=mod.feedback_local)
    runs = mod.ler_jsonl(tmp_path / "min" / "runs.jsonl")
    feedback = mod.ler_jsonl(tmp_path / "min" / "feedback.jsonl")
    assert {run["error"] for run in runs} == {None, "TimeoutError"}  # classe, não a mensagem
    assert all(run["inputs"] is None and run["outputs"] is None for run in runs)
    assert all(fb["comment"] is None and fb["value"] is None for fb in feedback)
    mod.exportar(iter(rows), desde=desde, ate=ate, destino=tmp_path / "full", maximo=100,
                 conteudo=True, feedback=mod.feedback_local)
    full = mod.ler_jsonl(tmp_path / "full" / "runs.jsonl")
    assert "TimeoutError: catalogo nao respondeu" in {run["error"] for run in full}
    comentarios = [fb["comment"] or "" for fb in mod.ler_jsonl(tmp_path / "full" / "feedback.jsonl")]
    assert any("cs_lookup" in comentario for comentario in comentarios)
    assert mod.classe_do_erro("ValueError('texto do usuário')") == "ValueError"


def test_export_refuses_to_mix_identities_and_never_writes_past_the_cap(tmp_path):
    mod = importlib.import_module("17_exportar_runs")
    rows = _rows_locais(mod)
    desde, ate = (mod.instante(value) for value in mod.JANELA_LOCAL)
    ident = mod.identidade(origem="local-sintetico", desde=desde, ate=ate, conteudo=False, feedback=True)
    assert mod.conferir_destino(tmp_path, ident) is None
    mod.exportar(iter(rows), desde=desde, ate=ate, destino=tmp_path, maximo=100)
    (tmp_path / "manifesto.json").write_text('{"identidade": ' + __import__("json").dumps(ident) + "}")
    assert mod.conferir_destino(tmp_path, ident) == {"identidade": ident}
    for outra in [dict(ident, conteudo=True), dict(ident, origem="langsmith-dcra-estudos"),
                  dict(ident, ate=mod.instante("2026-09-09T11:00:00Z").isoformat()),
                  dict(ident, feedback=False)]:
        with pytest.raises(SystemExit):
            mod.conferir_destino(tmp_path, outra)
    # JSONL sem manifesto também não é reaproveitado: não há como saber de onde veio.
    (tmp_path / "orfao").mkdir()
    (tmp_path / "orfao" / "runs.jsonl").write_text("{}\n")
    with pytest.raises(SystemExit):
        mod.conferir_destino(tmp_path / "orfao", ident)
    # Acima do teto nada é gravado: um arquivo parcial nunca passaria por completo.
    result = mod.exportar(iter(rows), desde=desde, ate=ate, destino=tmp_path / "teto", maximo=3)
    assert result["truncado"] and not (tmp_path / "teto").exists()
    with pytest.raises(ValueError):
        mod.exportar(iter(rows), desde=desde, ate=ate, destino=tmp_path / "zero", maximo=0)
    assert len(mod.slug(ident)) < 80 and mod.slug(dict(ident, conteudo=True)).endswith("-conteudo")


class _FakeRun:
    """Forma do `Run` da API v2: ancestrais em `parent_run_ids`, enums em maiúsculas, datas com fuso."""

    def __init__(self, id, start, error=None, parents=(), end=None):
        from datetime import UTC, datetime

        self.id, self.trace_id, self.parent_run_ids = id, f"t-{id}", list(parents)
        self.name, self.run_type, self.error = "dcra-iniciar", "CHAIN", error
        self.start_time = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(UTC)
        self.end_time = datetime.fromisoformat(end.replace("Z", "+00:00")).astimezone(UTC) if end else None
        self.status, self.tags = "ERROR" if error else "SUCCESS", ["estudo"]
        self.total_tokens, self.total_cost = 12, None
        self.inputs, self.outputs = {"text": "drop column x.y"}, {"risk": "LOW"}


class _FakeRuns:
    def __init__(self, runs, calls):
        self._runs, self._calls = runs, calls

    def query(self, **kwargs):
        self._calls.append(kwargs)

        async def pagina():
            for run in self._runs:
                yield run

        return pagina()


class _FakeClient:
    """Só a superfície v2 usada pelos labs: `aread_project` e `runs.query` assíncronos, feedback síncrono."""

    def __init__(self, runs):
        self.calls = []
        self.runs = _FakeRuns(runs, self.calls)

    async def aread_project(self, *, project_name):
        from types import SimpleNamespace

        return SimpleNamespace(id="00000000-0000-0000-0000-00000000c0de", name=project_name)

    def list_feedback(self, run_ids):
        return []


def test_remote_export_sends_both_bounds_to_the_server_and_detects_excess(tmp_path):
    import asyncio

    mod = importlib.import_module("17_exportar_runs")
    desde, ate = mod.instante("2026-09-01T00:00:00Z"), mod.instante("2026-09-02T00:00:00Z")
    client = _FakeClient([_FakeRun("r1", "2026-09-01T10:00:00Z", error="TimeoutError: catalogo x"),
                          _FakeRun("r2", "2026-09-01T11:00:00Z", parents=["r1"]),
                          _FakeRun("r3", "2026-09-01T12:00:00Z")])
    fonte = asyncio.run(mod.consultar_remoto(client, "dcra-estudos", desde, ate, maximo=2))
    result = mod.exportar(fonte, desde=desde, ate=ate, destino=tmp_path, maximo=2,
                          feedback=mod.feedback_remoto(client))
    call = client.calls[0]
    assert call["project_ids"] == ["00000000-0000-0000-0000-00000000c0de"]  # projeto por UUID, não por nome
    assert call["min_start_time"] == "2026-09-01T00:00:00Z"
    assert call["max_start_time"] == "2026-09-02T00:00:00Z"
    assert call["page_size"] == 3 and "INPUTS" not in call["selects"]  # maximo + 1; sem texto livre
    assert result["truncado"] and not (tmp_path / "runs.jsonl").exists()
    fonte = asyncio.run(mod.consultar_remoto(client, "dcra-estudos", desde, ate, maximo=3, conteudo=True))
    assert "INPUTS" in client.calls[1]["selects"]
    ok = mod.exportar(fonte, desde=desde, ate=ate, destino=tmp_path, maximo=3,
                      feedback=mod.feedback_remoto(client))
    assert ok["runs"] == {"novos": 3, "ja_presentes": 0, "fora_da_janela": 0}
    linhas = mod.ler_jsonl(tmp_path / "runs.jsonl")
    assert linhas[0]["error"] == "TimeoutError" and linhas[0]["inputs"] is None
    assert linhas[0]["start_time"] == "2026-09-01T10:00:00+00:00"
    assert (linhas[0]["status"], linhas[0]["run_type"]) == ("error", "chain")  # normalizados como o local
    assert linhas[1]["parent_run_id"] == "r1" and linhas[2]["parent_run_id"] is None  # último ancestral


def test_remote_aggregation_reads_the_v2_shape_and_refuses_truncated_samples():
    import asyncio

    mod = importlib.import_module("16_consultar_runs")
    runs = [_FakeRun("r1", "2026-09-01T10:00:00Z", end="2026-09-01T10:00:01Z"),
            _FakeRun("r2", "2026-09-01T10:00:00.2Z", end="2026-09-01T10:00:00.7Z", parents=["r1"]),
            _FakeRun("r3", "2026-09-01T11:00:00Z")]  # sem end_time: ainda em execução, fica de fora
    client = _FakeClient(runs)
    linhas = asyncio.run(mod.coletar_remoto(client, "dcra-estudos", dias=1, maximo=10))
    assert [(r["id"], r["parent"], r["run_type"]) for r in linhas] == [("r1", None, "chain"),
                                                                        ("r2", "r1", "chain")]
    assert "min_start_time" in client.calls[0] and client.calls[0]["selects"] == mod.CAMPOS
    with pytest.raises(SystemExit):
        asyncio.run(mod.coletar_remoto(client, "dcra-estudos", dias=1, maximo=1))


def test_platform_estimate_bills_ingestion_and_upgrades_as_separate_meters():
    mod = importlib.import_module("09_costs")
    est = mod.estimativa_mensal(traces_ingeridos=20_000, upgrades_no_mes=2_000,
                                tarifa=mod.TarifaPlataforma(), modelo_aplicacao=Decimal("12"),
                                juiz=Decimal("3"), armazenamento_externo=Decimal("1"))
    assert est["ingeridos_cobraveis"] == 15_000
    assert Decimal(est["plataforma_usd"]) == Decimal("86.5")
    # Erro A subestima (tira o promovido da ingestão); erro B superestima (cobra a ingestão de novo).
    assert Decimal(est["erro_a_promovido_sai_da_ingestao_usd"]) == Decimal("81.5")
    assert Decimal(est["erro_b_ingestao_cobrada_de_novo_usd"]) == Decimal("91.5")
    assert Decimal(est["total_usd"]) == Decimal("102.5")
    # Um mês sem ingestão ainda fatura upgrades de traces de meses anteriores.
    zero = Decimal(0)
    antigo = mod.estimativa_mensal(traces_ingeridos=0, upgrades_no_mes=500, tarifa=mod.TarifaPlataforma(),
                                   modelo_aplicacao=zero, juiz=zero, armazenamento_externo=zero)
    assert Decimal(antigo["parcelas_usd"]["ingestao"]) == 0
    assert Decimal(antigo["plataforma_usd"]) == Decimal("41.5")
    with pytest.raises(ValueError):
        mod.estimativa_mensal(traces_ingeridos=-1, upgrades_no_mes=0, tarifa=mod.TarifaPlataforma(),
                              modelo_aplicacao=Decimal(0), juiz=Decimal(0), armazenamento_externo=Decimal(0))
