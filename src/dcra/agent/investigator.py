"""The bounded read-only investigator agent (plan.md Project Structure).

A ReAct agent restricted to the three read-only evidence tools and a recursion cap. It runs only
when ``assess_risk`` set an evidence gap; it produces no risk or routing content (Constitution
II / IV).
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from dcra.domain.models import EvidenceItem, StructuredChange

_RECURSION_LIMIT = 8


_SYSTEM = (
    "You fill a specific evidence gap for a data-change risk review. "
    "Use ONLY the provided read-only tools. Do not speculate. "
    "When you have what the tools can give, stop."
)


def run_investigation(
    model: Any, *, change: StructuredChange, tools: list, gap_note: str
) -> list[EvidenceItem]:
    """Bounded read-only agent. Returns any additional EvidenceItems it gathered."""
    from langchain.agents import create_agent

    agent = create_agent(model, tools, system_prompt=_SYSTEM)
    prompt = (
        f"Change: {change.model_dump(mode='json')}. Gap: {gap_note}. "
        "Gather what the tools can tell you about it."
    )
    state = agent.invoke(
        {"messages": [("human", prompt)]},
        config={"recursion_limit": _RECURSION_LIMIT},
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
