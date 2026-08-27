"""Streamlit UI for the Data Change Risk Analyst.

Run:  uv run streamlit run src/dcra/app/streamlit_app.py

Shows the workflow advancing: interpretation → evidence (incl. unavailable) → risk + factors →
recommendation (labelled AI-generated) → for MEDIUM/HIGH the review gate (US2), for LOW an
auto-finalized record.
"""

from __future__ import annotations

import streamlit as st

from dcra.config import Settings
from dcra.domain.models import ChangeRequest, InterpretationError
from dcra.evidence.dataset import default_dataset
from dcra.graph.build import (
    build_graph,
    get_state,
    is_awaiting_review,
    pending_interrupt,
    resume,
    run,
)
from dcra.graph.deps import GraphDeps, production_deps
from dcra.graph.nodes import review_payload

st.set_page_config(page_title="Data Change Risk Analyst", layout="centered")
st.title("Data Change Risk Analyst")
st.caption("Assess the risk of a proposed data-asset change · human review before any decision")


@st.cache_resource
def _graph():
    settings = Settings.from_env()
    try:
        deps: GraphDeps = production_deps(settings, default_dataset())
    except Exception as exc:  # no API key / no DB — degrade to a clear message
        st.warning(f"LLM/DB not fully configured ({exc}); set up .env to run real analyses.")
        raise
    return build_graph(deps, checkpointer=_checkpointer(settings))


def _checkpointer(settings: Settings):
    from dcra.persistence.checkpointer import make_checkpointer

    return make_checkpointer(settings.database_url)


with st.form("submit"):
    text = st.text_input(
        "Proposed change",
        placeholder="e.g. Remove the column customer_legacy_id from the orders table",
    )
    who = st.text_input("Your name", value="data.engineer")
    submitted = st.form_submit_button("Analyze")

if submitted and text.strip():
    cr = ChangeRequest(raw_text=text.strip(), submitted_by=who or "anonymous")
    st.session_state["thread_id"] = cr.id
    try:
        state = run(_graph(), cr)
    except InterpretationError:
        state = {"error": "interpretation_failed"}
    st.session_state["state"] = state

state = st.session_state.get("state")
if state:
    if state.get("error"):
        st.error("That could not be interpreted as a recognised data change. Please restate it "
                 "(e.g. “drop column orders.status”, “add index on orders(customer_id)”).")
    else:
        st.subheader("Steps")
        for line in state.get("step_log", []):
            st.write("•", line)

        st.subheader("Evidence")
        for e in state.get("evidence", []):
            tag = "🟢" if e.status.value == "OBTAINED" else "🟠 unavailable"
            st.write(f"{tag} · **{e.kind.value}** · {e.key} · _{e.source}_")
            if e.payload:
                st.json(e.payload, expanded=False)

        risk = state.get("risk")
        if risk:
            st.subheader(f"Risk: {risk.category.value}")
            for f in risk.factors:
                st.write(f"- **{f.code}** ({f.severity.value}) — {f.description}")

        recs = state.get("recommendations", [])
        if recs:
            r = recs[-1]
            st.subheader("Recommendation  ·  🤖 AI-generated (non-binding)")
            st.write(f"**{r.disposition.value}** · confidence {r.confidence.value}")
            st.write(r.rationale)
            if r.mitigations:
                st.write("Mitigations:", ", ".join(r.mitigations))

        thread_id = st.session_state.get("thread_id")
        payload = pending_interrupt(state)
        if payload is None and thread_id and not state.get("outcome"):
            try:
                if is_awaiting_review(_graph(), thread_id):
                    payload = review_payload(state)
            except Exception:
                payload = None

        if state.get("outcome"):
            actions = state.get("review_actions", [])
            how = "auto-finalized, no human review" if not actions else (
                f"human decision by {actions[-1].reviewer}"
            )
            st.success(f"Final record: {state['outcome'].value} ({how})")
            if actions:
                st.caption("AI recommendation and human decision are recorded as separate fields.")

        elif payload is not None:
            st.divider()
            st.subheader("Human review")
            st.caption(
                f"Risk {payload['risk']['category']} · revisions left "
                f"{payload['revisions_remaining']}"
            )
            reviewer = st.text_input("Reviewer name", value="data.owner", key="rv")
            col_a, col_b, col_c = st.columns(3)
            decided = None
            if col_a.button("Approve", use_container_width=True):
                decided = {"decision": "APPROVE", "reviewer": reviewer}
            if col_b.button("Reject", use_container_width=True):
                decided = {"decision": "REJECT", "reviewer": reviewer}
            if "RETURN" in payload["options"]:
                note = st.text_area("Return with a note", key="rn")
                miss = st.checkbox("Mark: evidence missing (re-runs risk assessment)")
                if col_c.button("Return for revision", use_container_width=True):
                    decided = {
                        "decision": "RETURN", "reviewer": reviewer,
                        "note": note, "evidence_missing": miss,
                    }
            if decided is not None:
                st.session_state["state"] = resume(_graph(), thread_id, decided)
                st.rerun()

with st.expander("Reopen a case by id"):
    tid = st.text_input("thread_id")
    if st.button("Reopen") and tid:
        try:
            st.session_state["thread_id"] = tid
            st.session_state["state"] = get_state(_graph(), tid)
            st.rerun()
        except Exception as exc:
            st.error(f"Could not reopen: {exc}")
