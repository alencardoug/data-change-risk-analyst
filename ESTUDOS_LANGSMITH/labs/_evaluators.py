"""Mesmas métricas usadas localmente e em Client.evaluate; gabarito independente."""

from __future__ import annotations


def risk_correct(outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "risk_correct", "score": int(outputs.get("risk") == reference_outputs["risk"])}


def review_correct(outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "review_correct",
            "score": int(outputs.get("awaiting_review") == reference_outputs["awaiting_review"])}


def factors_exact(outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "factors_exact",
            "score": int(set(outputs.get("factors", [])) == set(reference_outputs["factors"]))}


def error_contract(outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "error_contract",
            "score": int(bool(outputs.get("error")) == reference_outputs.get("error", False))}


EVALUATORS = [risk_correct, review_correct, factors_exact, error_contract]


def high_risk_recall(rows: list[dict]) -> float | None:
    high = [row for row in rows if row["reference"]["risk"] == "HIGH"]
    if not high:
        return None  # Não confundir denominador vazio com sucesso.
    return sum(row["outputs"].get("risk") == "HIGH" for row in high) / len(high)
