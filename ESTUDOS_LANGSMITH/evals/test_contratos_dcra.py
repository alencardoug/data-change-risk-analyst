"""Contratos do DCRA como testes: um caso por teste e uma métrica de conjunto que asserts não substituem."""

from __future__ import annotations

import pytest
from _common import read_cases
from _evaluators import EVALUATORS, high_risk_recall
from _suite import POLITICA, resultados
from langsmith import testing as t

CASES = {case["id"]: case for case in read_cases()}
EXPECTED_IDS = sorted(CASES)


@pytest.mark.langsmith
@pytest.mark.parametrize("case_id", EXPECTED_IDS)
def test_caso_respeita_os_contratos(case_id: str) -> None:
    from _dcra import target

    case = CASES[case_id]
    suite = resultados()
    # Só os inputs entram no target; a referência fica fora do grafo e vira gabarito do exemplo remoto.
    t.log_inputs(case["inputs"])
    t.log_reference_outputs(case["outputs"])
    outputs = target(case["inputs"], variant=suite.variant)
    t.log_outputs(outputs)
    scores = {}
    for evaluator in EVALUATORS:
        metric = evaluator(outputs, case["outputs"])
        scores[metric["key"]] = metric["score"]
        t.log_feedback(key=metric["key"], score=metric["score"])
    # Registrar antes de qualquer assert: a métrica de conjunto precisa da linha mesmo quando o caso falha.
    suite.registrar(case, outputs, scores)
    failing = [key for key, score in scores.items() if score != 1]
    assert not failing, (
        f"{case_id} ({suite.variant}) falhou em {failing}: obtido risk={outputs.get('risk')} "
        f"awaiting_review={outputs.get('awaiting_review')}; esperado risk={case['outputs']['risk']} "
        f"awaiting_review={case['outputs']['awaiting_review']}"
    )


def test_conjunto_completo_com_recall_high() -> None:
    """Recall HIGH é calculado sobre todas as referências HIGH; cada id conta exatamente uma vez.

    Sem `@pytest.mark.langsmith` de propósito: o plugin sincroniza cada teste marcado como um
    exemplo do dataset, e um agregado não é um caso de negócio. O conjunto vive no relatório local.
    """
    suite = resultados()
    ids = sorted(row["case_id"] for row in suite.rows)
    assert ids == EXPECTED_IDS, (
        f"Esperados {len(EXPECTED_IDS)} casos, avaliados {len(ids)}. "
        "Um subconjunto (-k) invalida a métrica de conjunto; este teste falha de propósito."
    )
    metrics = suite.metrics()
    recall = high_risk_recall(suite.rows)
    assert recall == POLITICA["high_risk_recall"], (
        f"recall HIGH={recall} ({suite.variant}); nenhum HIGH pode virar outra categoria")
    assert metrics["risk_correct"] >= POLITICA["risk_correct_min"], metrics
    assert metrics["review_correct"] == POLITICA["review_correct"], metrics
