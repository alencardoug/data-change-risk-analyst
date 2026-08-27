"""T027 — opt-in: the real model returns a schema-valid StructuredChange.

Run with:  RUN_LLM_TESTS=1 uv run pytest tests/llm_integration
"""

import pytest

from tests.conftest import requires_llm

pytestmark = [requires_llm(), pytest.mark.llm]


@pytest.mark.parametrize(
    "text",
    [
        "Remove the column customer_legacy_id from the orders table.",
        "Make orders.status nullable.",
        "Add an index on orders(customer_id).",
    ],
)
def test_real_interpretation_is_schema_valid(text):
    from dcra.config import Settings
    from dcra.llm.factory import build_chat_model, interpret

    sc = interpret(build_chat_model(Settings.from_env()), text)
    assert sc.target_table
    assert sc.operation.value in {"DROP_COLUMN", "ALTER_COLUMN", "ADD_INDEX"}
