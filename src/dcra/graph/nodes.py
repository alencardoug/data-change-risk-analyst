"""Graph nodes. Each is a closure over GraphDeps. Contract: contracts/graph-state.md."""

from __future__ import annotations

from dcra.domain.enums import CaseStatus, Outcome, ReviewDecision, RiskCategory
from dcra.domain.models import AnalysisRecord, EvidenceItem, RiskAssessment
from dcra.evidence.tools import read_asset_metadata, read_dependencies, read_downstream_usage
from dcra.graph.deps import GraphDeps
from dcra.graph.state import GraphState
from dcra.rules import risk as risk_rules


def make_nodes(deps: GraphDeps) -> dict:
    def interpret(state: GraphState) -> dict:
        cr = state["change_request"]
        # InterpretationError propagates out of the graph; run() catches it (FR-002: no record).
        sc = deps.interpret_fn(cr.raw_text)
        return {
            "structured_change": sc,
            "status": CaseStatus.COLLECTING_EVIDENCE,
            "step_log": [f"interpret: {sc.operation.value} on {sc.target_table}"],
        }

    def _target_column(sc) -> str:
        return sc.target_column or (sc.index_columns[0] if sc.index_columns else "")

    def collect_asset(state: GraphState) -> dict:
        sc = state["structured_change"]
        items = read_asset_metadata(deps.dataset, sc.target_table, _target_column(sc) or None)
        return {"evidence": items, "step_log": [f"collect_asset: {len(items)} item(s)"]}

    def collect_deps(state: GraphState) -> dict:
        sc = state["structured_change"]
        items = read_dependencies(deps.dataset, sc.target_table, _target_column(sc))
        return {"evidence": items, "step_log": [f"collect_deps: {len(items)} item(s)"]}

    def collect_usage(state: GraphState) -> dict:
        sc = state["structured_change"]
        items = read_downstream_usage(deps.dataset, sc.target_table, _target_column(sc))
        return {"evidence": items, "step_log": [f"collect_usage: {len(items)} item(s)"]}

    def assess_risk(state: GraphState) -> dict:
        sc = state["structured_change"]
        evidence = state.get("evidence", [])
        assessment = risk_rules.assess(sc, evidence)
        gap = risk_rules.has_evidence_gap(sc, evidence)
        return {
            "risk": assessment,
            "risk_history": [assessment],
            "evidence_gap": gap,
            "status": CaseStatus.ASSESSING_RISK,
            "step_log": [
                f"assess_risk: {assessment.category.value} "
                f"({', '.join(f.code for f in assessment.factors)})"
                + ("; evidence gap" if gap else "")
            ],
        }

    def investigate(state: GraphState) -> dict:
        sc = state["structured_change"]
        prior = state.get("risk")
        found: list[EvidenceItem] = deps.investigate_fn(
            change=sc, gap_note="dependency/usage evidence was unavailable"
        )
        merged = state.get("evidence", []) + found
        reassessed: RiskAssessment = risk_rules.assess(sc, merged)
        reassessed = reassessed.model_copy(
            update={"pass_number": (prior.pass_number if prior else 1) + 1}
        )
        return {
            "evidence": found,
            "risk": reassessed,
            "risk_history": [reassessed],
            "evidence_gap": False,
            "status": CaseStatus.INVESTIGATING,
            "step_log": [
                f"investigate: agent added {len(found)} item(s); "
                f"risk now {reassessed.category.value}"
            ],
        }

    def recommend(state: GraphState) -> dict:
        sc = state["structured_change"]
        evidence = state.get("evidence", [])
        risk = state["risk"]
        actions = state.get("review_actions", [])
        note = None
        if actions and actions[-1].decision == ReviewDecision.RETURN:
            note = actions[-1].note
        version = len(state.get("recommendations", [])) + 1
        rec = deps.recommend_fn(
            change=sc, evidence=evidence, risk=risk, note=note, version=version
        )
        return {
            "recommendations": [rec],
            "status": CaseStatus.RECOMMENDING,
            "step_log": [
                f"recommend: v{rec.version} {rec.disposition.value} ({rec.confidence.value})"
            ],
        }

    def finalize(state: GraphState) -> dict:
        recs = state.get("recommendations", [])
        actions = state.get("review_actions", [])
        reviewed = bool(actions)
        if not reviewed:
            outcome = Outcome.AUTO_FINALIZED
        elif actions[-1].decision == ReviewDecision.APPROVE:
            outcome = Outcome.APPROVED
        else:
            outcome = Outcome.REJECTED
        final_version = recs[-1].version if recs else 0
        step = [f"finalize: {outcome.value}" + ("" if reviewed else " (auto, no human review)")]
        record = AnalysisRecord(
            id=state["change_request"].id,
            change_request=state["change_request"],
            structured_change=state.get("structured_change"),
            evidence=state.get("evidence", []),
            risk_assessments=state.get("risk_history", []),
            recommendations=recs,
            review_actions=actions,
            reviewed=reviewed,
            outcome=outcome,
            final_recommendation_version=final_version,
            step_log=state.get("step_log", []) + step,
        )
        if deps.repository is not None:
            deps.repository.save(record)
        return {"outcome": outcome, "status": CaseStatus.FINALIZED, "step_log": step}

    return {
        "interpret": interpret,
        "collect_asset": collect_asset,
        "collect_deps": collect_deps,
        "collect_usage": collect_usage,
        "assess_risk": assess_risk,
        "investigate": investigate,
        "recommend": recommend,
        "finalize": finalize,
    }


def route_after_assess(state: GraphState) -> str:
    return "investigate" if state.get("evidence_gap") else "recommend"


def route_after_recommend(state: GraphState) -> str:
    """US1: LOW auto-finalizes; anything else ends here (US2 repoints to human_review)."""
    risk = state.get("risk")
    if risk and risk.category == RiskCategory.LOW:
        return "finalize"
    return "stop"
