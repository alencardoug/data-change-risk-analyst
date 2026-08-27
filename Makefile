.PHONY: help sync test e2e unit llm-test lint fmt db app graph

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n", $$1, $$2}'

sync:  ## Install/refresh the environment
	uv sync

test:  ## Deterministic tests (no API key, no DB)
	uv run pytest tests/unit tests/e2e -q

unit:  ## Unit tests only
	uv run pytest tests/unit -q

e2e:  ## End-to-end graph tests only
	uv run pytest tests/e2e -q

llm-test:  ## Opt-in tests that call a real model
	RUN_LLM_TESTS=1 uv run pytest tests/llm_integration -q

lint:  ## Ruff check
	uv run ruff check src tests

fmt:  ## Ruff format + fix
	uv run ruff format src tests && uv run ruff check --fix src tests

db:  ## Start Postgres
	docker compose up -d

app:  ## Run the Streamlit demo
	uv run streamlit run src/dcra/app/streamlit_app.py

graph:  ## Print the compiled graph as mermaid
	uv run python -c "from tests.conftest import keyword_interpret, fake_recommend, fake_investigate; \
from dcra.graph.deps import GraphDeps; from dcra.evidence.dataset import default_dataset; \
from dcra.graph.build import build_graph; \
print(build_graph(GraphDeps(keyword_interpret, fake_recommend(), fake_investigate(), default_dataset())).get_graph().draw_mermaid())"
