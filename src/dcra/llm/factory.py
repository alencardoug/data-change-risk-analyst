"""LLM-backed steps. Contract: specs/001-data-change-risk-review/contracts/llm-schemas.md.

The graph never calls these directly; it holds three callables on ``GraphDeps`` so tests can
inject deterministic fakes. Production wires the functions below.

Structured output is provider-native via ``.with_structured_output``. The LLM never produces the
risk category or any routing decision (Constitution IV).
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from dcra.config import Settings
from dcra.domain.enums import Confidence, Disposition, EvidenceStatus
from dcra.domain.models import (
    EvidenceItem,
    InterpretationError,
    Recommendation,
    RiskAssessment,
    StructuredChange,
)

_INTERPRET_SYS = (
    "You convert a one-line data-change request into a structured change. "
    "Recognised operations: DROP_COLUMN, ALTER_COLUMN (type/nullability), ADD_INDEX. "
    "DROP_COLUMN/ALTER_COLUMN need target_table + target_column. ADD_INDEX needs target_table + "
    "index_columns. If the text is not one of these against a named table, set operation to a "
    "best guess but low confidence; the caller validates."
)

_RECOMMEND_SYS = (
    "You draft a NON-BINDING recommendation about a proposed data change. You are given the "
    "structured change, the evidence gathered (including items marked unavailable), the risk "
    "category and its factors, and possibly a reviewer note. Use ONLY the supplied evidence and "
    "factors; do not invent dependencies or usage. Choose disposition PROCEED, "
    "PROCEED_WITH_MITIGATION (then list mitigations), or DO_NOT_PROCEED."
)


def build_chat_model(settings: Settings) -> Any:
    if settings.llm_provider != "anthropic":  # pragma: no cover - single provider in V0
        raise ValueError(f"unsupported LLM provider: {settings.llm_provider}")
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(model=settings.llm_model, temperature=0, max_retries=2)


def interpret(model: Any, raw_text: str) -> StructuredChange:
    parser = model.with_structured_output(StructuredChange)
    messages = [("system", _INTERPRET_SYS), ("human", raw_text)]
    try:
        result = parser.invoke(messages)
        return _coerce_structured(result)
    except (ValidationError, ValueError) as first:
        try:
            result = parser.invoke(
                messages + [("human", f"That failed validation: {first}. Try again.")]
            )
            return _coerce_structured(result)
        except (ValidationError, ValueError) as second:
            raise InterpretationError(str(second)) from second


def _coerce_structured(result: Any) -> StructuredChange:
    if isinstance(result, StructuredChange):
        return result
    return StructuredChange.model_validate(result)


def draft_recommendation(
    model: Any,
    *,
    change: StructuredChange,
    evidence: list[EvidenceItem],
    risk: RiskAssessment,
    note: str | None,
    version: int,
) -> Recommendation:
    parser = model.with_structured_output(Recommendation)
    reduced = any(e.status == EvidenceStatus.UNAVAILABLE for e in evidence)
    ctx = {
        "change": change.model_dump(mode="json"),
        "evidence": [e.model_dump(mode="json") for e in evidence],
        "risk_category": risk.category.value,
        "risk_factors": [f.model_dump(mode="json") for f in risk.factors],
        "reviewer_note": note,
    }
    human = f"Draft the recommendation for this context:\n{ctx}"
    try:
        rec = _coerce_rec(parser.invoke([("system", _RECOMMEND_SYS), ("human", human)]))
    except (ValidationError, ValueError):
        try:
            rec = _coerce_rec(
                parser.invoke([("system", _RECOMMEND_SYS), ("human", human + "\nReturn valid JSON.")])
            )
        except (ValidationError, ValueError):
            rec = Recommendation(
                disposition=Disposition.DO_NOT_PROCEED,
                rationale="The recommendation draft could not be produced; a human decision is required.",
            )
    return _normalise_rec(rec, version=version, note=note, reduced=reduced)


def _coerce_rec(result: Any) -> Recommendation:
    if isinstance(result, Recommendation):
        return result
    return Recommendation.model_validate(result)


def _normalise_rec(
    rec: Recommendation, *, version: int, note: str | None, reduced: bool
) -> Recommendation:
    data = rec.model_dump()
    data["version"] = version
    data["ai_generated"] = True
    data["prompted_by_note"] = note
    if reduced:
        data["confidence"] = Confidence.REDUCED
    if data["disposition"] == Disposition.PROCEED_WITH_MITIGATION and not data["mitigations"]:
        data["disposition"] = Disposition.DO_NOT_PROCEED
        data["rationale"] = (data["rationale"] + " (mitigations were unspecified)").strip()
    return Recommendation.model_validate(data)


def run_investigation(
    model: Any, *, change: StructuredChange, tools: list, gap_note: str
) -> list[EvidenceItem]:
    """Bounded read-only ReAct agent. Returns any additional EvidenceItems it gathered."""
    from langgraph.prebuilt import create_react_agent

    agent = create_react_agent(model, tools)
    prompt = (
        "You are filling a specific evidence gap for a data-change risk review. "
        f"Change: {change.model_dump(mode='json')}. Gap: {gap_note}. "
        "Use ONLY the provided read-only tools. Do not speculate. "
        "When you have what the tools can give, stop."
    )
    state = agent.invoke(
        {"messages": [("human", prompt)]},
        config={"recursion_limit": 8},
    )
    found: list[EvidenceItem] = []
    for msg in state["messages"]:
        if getattr(msg, "type", None) == "tool":
            content = msg.content
            items = content if isinstance(content, list) else [content]
            for raw in items:
                if isinstance(raw, dict):
                    try:
                        found.append(EvidenceItem.model_validate(raw))
                    except ValidationError:
                        continue
    return found
