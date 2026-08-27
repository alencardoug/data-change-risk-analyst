"""Compile the LangGraph workflow. Contract: contracts/graph-state.md.

US1 scope: interpret -> (fan-out) collect_asset|collect_deps|collect_usage -> (fan-in)
assess_risk -> [investigate] -> recommend -> LOW ? finalize : END.
US2/US3 add the human_review node and the revision loop.
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from dcra.domain.enums import CaseStatus
from dcra.domain.models import ChangeRequest, InterpretationError
from dcra.graph.deps import GraphDeps
from dcra.graph.nodes import make_nodes, route_after_assess, route_after_recommend
from dcra.graph.state import GraphState


def build_graph(deps: GraphDeps, checkpointer: Any | None = None) -> Any:
    nodes = make_nodes(deps)
    g = StateGraph(GraphState)

    for name, fn in nodes.items():
        g.add_node(name, fn)

    g.add_edge(START, "interpret")
    # fan-out (an InterpretationError raised in `interpret` propagates out; run() catches it)
    g.add_edge("interpret", "collect_asset")
    g.add_edge("interpret", "collect_deps")
    g.add_edge("interpret", "collect_usage")
    # fan-in: assess_risk runs once after all three collectors
    g.add_edge("collect_asset", "assess_risk")
    g.add_edge("collect_deps", "assess_risk")
    g.add_edge("collect_usage", "assess_risk")

    g.add_conditional_edges(
        "assess_risk",
        route_after_assess,
        {"investigate": "investigate", "recommend": "recommend"},
    )
    g.add_edge("investigate", "recommend")
    g.add_conditional_edges(
        "recommend", route_after_recommend, {"finalize": "finalize", "stop": END}
    )
    g.add_edge("finalize", END)

    return g.compile(checkpointer=checkpointer or MemorySaver())


def run(compiled: Any, change_request: ChangeRequest) -> GraphState:
    """Run a case. On interpretation failure, return a minimal state with ``error`` set and no
    record written (FR-002)."""
    config = {"configurable": {"thread_id": change_request.id}, "recursion_limit": 40}
    initial: GraphState = {
        "change_request": change_request,
        "revision_count": 0,
        "status": CaseStatus.INTERPRETING,
    }
    try:
        return compiled.invoke(initial, config=config)
    except InterpretationError as exc:
        return {
            "change_request": change_request,
            "structured_change": None,
            "status": CaseStatus.INTERPRETING,
            "error": f"interpretation_failed: {exc}",
            "step_log": ["interpret: failed — request not understood"],
        }


def resume(compiled: Any, thread_id: str, value: Any) -> GraphState:
    from langgraph.types import Command

    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 40}
    return compiled.invoke(Command(resume=value), config=config)


def get_state(compiled: Any, thread_id: str) -> GraphState:
    config = {"configurable": {"thread_id": thread_id}}
    return compiled.get_state(config).values
