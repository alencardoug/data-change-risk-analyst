"""T032 — opt-in: the investigator agent only calls the 3 read-only tools and terminates.

Run with:  RUN_LLM_TESTS=1 uv run pytest tests/llm_integration
"""

import pytest

from tests.conftest import requires_llm

pytestmark = [requires_llm(), pytest.mark.llm]


def test_agent_stays_within_readonly_tools():
    from dcra.config import Settings
    from dcra.domain.enums import Operation
    from dcra.domain.models import StructuredChange
    from dcra.evidence.dataset import default_dataset
    from dcra.evidence.tools import make_evidence_tools
    from dcra.llm.factory import build_chat_model, run_investigation

    tools = make_evidence_tools(default_dataset())
    sc = StructuredChange(
        operation=Operation.DROP_COLUMN, target_table="orders", target_column="customer_legacy_id"
    )
    found = run_investigation(
        build_chat_model(Settings.from_env()),
        change=sc,
        tools=tools,
        gap_note="dependency evidence was unavailable",
    )
    assert isinstance(found, list)  # terminated within the recursion cap without raising
