"""Adaptadores didáticos: reutilizam grafo e política reais com dependências locais."""

from __future__ import annotations

import re

from dcra.domain.enums import Confidence, Disposition, EvidenceStatus
from dcra.domain.models import ChangeRequest, InterpretationError, Recommendation, StructuredChange
from dcra.evidence.dataset import default_dataset
from dcra.graph.build import build_graph, pending_interrupt, resume, run
from dcra.graph.deps import GraphDeps


def interpret_fixture(raw: str) -> StructuredChange:
    """Parser pequeno, deliberadamente limitado. Não representa a qualidade de um LLM."""
    if m := re.fullmatch(r"(drop|alter) column\s+(\w+)\.(\w+)", raw.strip(), re.I):
        return StructuredChange(
            operation="DROP_COLUMN" if m[1].lower() == "drop" else "ALTER_COLUMN",
            target_table=m[2], target_column=m[3],
            alter_detail="mudança de tipo" if m[1].lower() == "alter" else None,
        )
    if m := re.fullmatch(r"add index on\s+(\w+)\s*\(([^)]+)\)", raw.strip(), re.I):
        return StructuredChange(
            operation="ADD_INDEX", target_table=m[1],
            index_columns=[c.strip() for c in m[2].split(",")],
        )
    if m := re.fullmatch(r"remove (?:the )?column\s+(\w+)\s+from (?:the )?(\w+)(?: table)?",
                         raw.strip(), re.I):
        return StructuredChange(operation="DROP_COLUMN", target_table=m[2], target_column=m[1])
    raise InterpretationError("O parser fixture não reconhece este pedido.")


def recommend_fixture(*, change, evidence, risk, note, version) -> Recommendation:
    factors = ", ".join(f.code for f in risk.factors)
    return Recommendation(
        version=version,
        disposition=Disposition.DO_NOT_PROCEED,
        rationale=f"Exemplo didático. Risco {risk.category.value}; fatores: {factors}.",
        confidence=Confidence.REDUCED if any(
            e.status == EvidenceStatus.UNAVAILABLE for e in evidence
        ) else Confidence.NORMAL,
        prompted_by_note=note,
    )


def make_deps(disabled: list[str] | None = None, *, real: bool = False) -> GraphDeps:
    ds = default_dataset(disabled_sources=set(disabled or []))
    if real:
        from _common import real_model

        from dcra.agent.investigator import run_investigation
        from dcra.evidence.tools import make_evidence_tools
        from dcra.llm.factory import draft_recommendation, interpret

        model = real_model()
        return GraphDeps(
            interpret_fn=lambda raw: interpret(model, raw),
            recommend_fn=lambda **kw: draft_recommendation(model, **kw),
            investigate_fn=lambda **kw: run_investigation(model, tools=make_evidence_tools(ds), **kw),
            dataset=ds,
        )
    return GraphDeps(
        interpret_fn=interpret_fixture, recommend_fn=recommend_fixture,
        investigate_fn=lambda **kw: [], dataset=ds,
    )


def summarize(state: dict, thread_id: str) -> dict:
    risk = state.get("risk")
    sc = state.get("structured_change")
    return {
        "thread_id": thread_id,
        "risk": risk.category.value if risk else None,
        "factors": sorted(f.code for f in risk.factors) if risk else [],
        "awaiting_review": pending_interrupt(state) is not None,
        "outcome": state.get("outcome"),
        "error": state.get("error"),
        "structured_change": sc.model_dump(mode="json") if sc else None,
        "recommendation_versions": [r.version for r in state.get("recommendations", [])],
        "risk_passes": len(state.get("risk_history", [])),
        "step_log": state.get("step_log", []),
    }


def target(inputs: dict, *, variant: str = "baseline") -> dict:
    """O target recebe apenas inputs. Gabaritos nunca entram no grafo."""
    graph = build_graph(make_deps(inputs.get("disabled_sources")))
    cr = ChangeRequest(raw_text=inputs["text"], submitted_by="aluno-sintetico")
    state = run(graph, cr)
    out = summarize(state, cr.id)
    if variant == "bug" and out["risk"] == "HIGH":
        # Mutação APENAS no adaptador de estudo: demonstra uma regressão que deve ser detectada.
        out["risk"] = "LOW"
        out["awaiting_review"] = False
    return out


def review(graph, thread_id: str, decision: str, *, evidence_missing: bool = False) -> dict:
    return resume(graph, thread_id, {
        "decision": decision, "reviewer": "revisor-sintetico",
        "note": "Explique melhor os fatores observados." if decision == "RETURN" else None,
        "evidence_missing": evidence_missing,
    })
