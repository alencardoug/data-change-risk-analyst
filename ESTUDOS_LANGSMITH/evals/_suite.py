"""Estado compartilhado da suíte: variante escolhida e linhas registradas por caso.

Fica fora da assinatura dos testes de propósito: `@pytest.mark.langsmith` captura todo
argumento do teste como input do exemplo remoto, e um objeto coletor não pertence ao dataset.
"""

from __future__ import annotations

VARIANTS = ("baseline", "bug")
CONTEXT: dict = {}

# Política do gate, num só lugar: o teste de conjunto a aplica e o relatório a registra.
POLITICA = {"versao": "contratos-v1", "risk_correct_min": 0.95, "high_risk_recall": 1.0,
            "review_correct": 1.0, "exige_conjunto_completo": True}


class Resultados:
    """Linhas de todos os casos; a métrica de conjunto precisa delas, não de asserts isolados."""

    def __init__(self, variant: str) -> None:
        self.variant = variant
        self.rows: list[dict] = []

    def registrar(self, case: dict, outputs: dict, scores: dict) -> None:
        self.rows.append({"case_id": case["id"], "slice": case["metadata"]["slice"],
                          "outputs": outputs, "reference": case["outputs"], "scores": scores})

    def metrics(self) -> dict:
        keys = sorted({key for row in self.rows for key in row["scores"]})
        return {key: sum(row["scores"][key] for row in self.rows) / len(self.rows) for key in keys}


def resultados() -> Resultados:
    return CONTEXT["resultados"]
