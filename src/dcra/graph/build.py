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
from dcra.graph.nodes import (
    make_nodes,
    route_after_assess,
    route_after_recommend,
    route_after_review,
)
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
        "recommend", route_after_recommend, {"finalize": "finalize", "review": "human_review"}
    )
    g.add_conditional_edges(
        "human_review",
        lambda s: route_after_review(s, deps.revision_limit),
        {"finalize": "finalize", "revise": "recommend", "reassess": "reassess_gate"},
    )
    # reassess loop: re-collect evidence in parallel, then assess_risk fans in again
    g.add_edge("reassess_gate", "collect_asset")
    g.add_edge("reassess_gate", "collect_deps")
    g.add_edge("reassess_gate", "collect_usage")
    g.add_edge("finalize", END)

    if checkpointer is None:
        from dcra.persistence.serde import dcra_serde

        checkpointer = MemorySaver(serde=dcra_serde())
    return g.compile(checkpointer=checkpointer)


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
    """Resume a paused run. A review decision (dict with a ``decision`` key) is validated to a
    ``ReviewAction`` here, so an invalid one (e.g. a blank RETURN note) raises cleanly without
    touching graph state (FR-016)."""
    from langgraph.types import Command

    from dcra.domain.models import ReviewAction

    if isinstance(value, dict) and "decision" in value:
        value = ReviewAction.model_validate(value)
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 40}
    return compiled.invoke(Command(resume=value), config=config)


def get_state(compiled: Any, thread_id: str) -> GraphState:
    config = {"configurable": {"thread_id": thread_id}}
    return compiled.get_state(config).values


def pending_interrupt(result: Any) -> dict | None:
    """Return the human-review payload if the run is paused at the gate, else None."""
    interrupts = result.get("__interrupt__") if isinstance(result, dict) else None
    if not interrupts:
        return None
    first = interrupts[0]
    return getattr(first, "value", first)


def is_awaiting_review(compiled: Any, thread_id: str) -> bool:
    snap = compiled.get_state({"configurable": {"thread_id": thread_id}})
    return bool(snap.next) and "human_review" in snap.next


def list_open_cases(
    compiled: Any, *, limit: int = 5, scan: int = 60
) -> list[tuple[str, str]]:
    """The most recent cases paused at the human-review gate, newest first.

    Returns ``(thread_id, label)`` pairs. ``scan`` bounds how many raw checkpoints we walk
    before giving up (there are several per thread); ``limit`` caps the returned list. Reads
    only the checkpointer — no schema of its own. Best-effort: returns ``[]`` on any error or
    when the checkpointer cannot enumerate threads (e.g. MemorySaver in another process)."""
    try:
        checkpointer = compiled.checkpointer
        # Materialise fully: calling compiled.get_state() while the .list() generator is still
        # open would re-enter the saver's non-reentrant lock on the same connection (deadlock).
        tuples = list(checkpointer.list(None, limit=scan))
    except Exception:
        return []

    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for tup in tuples:
        tid = tup.config.get("configurable", {}).get("thread_id")
        if not tid or tid in seen:
            continue
        seen.add(tid)
        try:
            snap = compiled.get_state({"configurable": {"thread_id": tid}})
        except Exception:
            continue
        if not (snap.next and "human_review" in snap.next):
            continue
        vals = snap.values or {}
        cr = vals.get("change_request")
        risk = vals.get("risk")
        raw = (getattr(cr, "raw_text", "") or "").strip().replace("\n", " ")
        who = getattr(cr, "submitted_by", "") or "?"
        cat = risk.category.value if risk else "?"
        label = f"{raw[:60] or '(sem texto)'} · {cat} · {who}"
        out.append((tid, label))
        if len(out) >= limit:
            break
    return out
