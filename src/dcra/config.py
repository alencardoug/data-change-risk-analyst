"""Runtime settings, loaded from environment (.env supported via python-dotenv)."""

from __future__ import annotations

import os
from dataclasses import dataclass

try:  # optional convenience; never required
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


@dataclass(frozen=True)
class Settings:
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    database_url: str | None = None
    langsmith_tracing: bool = False
    revision_limit: int = 2

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "openai"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o"),
            database_url=os.getenv("DATABASE_URL") or None,
            langsmith_tracing=os.getenv("LANGSMITH_TRACING", "").lower() in ("1", "true", "yes"),
            revision_limit=int(os.getenv("DCRA_REVISION_LIMIT", "2")),
        )
