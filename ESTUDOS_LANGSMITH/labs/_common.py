"""Infraestrutura dos laboratórios; nenhum envio sem --send, nenhum LLM implícito."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from importlib.metadata import version
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv

COURSE = Path(__file__).resolve().parents[1]
ROOT = COURSE.parent
ARTIFACTS = COURSE / "artefatos"
sys.path.insert(0, str(ROOT / "src"))


def parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--send", action="store_true", help="Envia dados sintéticos ao seu LangSmith.")
    p.add_argument("--project", default=os.getenv("DCRA_LAB_PROJECT", "dcra-estudos"))
    return p


def configure(args: argparse.Namespace) -> None:
    # Definido ANTES de dcra.config importar/carregar .env. O flag do laboratório manda.
    enabled = "true" if args.send else "false"
    os.environ["LANGSMITH_TRACING"] = enabled
    os.environ["LANGCHAIN_TRACING_V2"] = enabled
    load_dotenv(ROOT / ".env", override=False)
    os.environ["LANGSMITH_PROJECT"] = args.project
    if args.send and not credential_present("LANGSMITH_API_KEY"):
        raise SystemExit("Preencha LANGSMITH_API_KEY em .env para usar --send. Veja 03-preparacao.md.")


def credential_present(name: str) -> bool:
    value = os.getenv(name, "").strip()
    return bool(value and "..." not in value and not value.startswith("<"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest() -> dict[str, Any]:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    paths = sorted((COURSE / "labs").glob("*.py"))
    paths += sorted((COURSE / "evals").glob("*.py"))  # coleta, agregação e política do gate
    paths += sorted((ROOT / "src" / "dcra").rglob("*.py"))
    paths += sorted((COURSE / "dados").glob("*.json*"))
    paths += [ROOT / "uv.lock", ROOT / "pyproject.toml"]
    return {
        "git_sha": result.stdout.strip() or "indisponivel",
        "working_tree_dirty": bool(status.stdout.strip()),
        "python": platform.python_version(),
        "packages": {name: version(name) for name in ["langsmith", "langchain", "langgraph"]},
        "file_sha256": {str(p.relative_to(ROOT)): digest(p) for p in paths if p.exists()},
        "evaluator_version": "contratos-v1",
    }


def write_json(name: str, value: Any) -> Path:
    ARTIFACTS.mkdir(exist_ok=True)
    path = ARTIFACTS / name
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")
    print(f"Arquivo: {path.relative_to(ROOT)}")
    return path


def read_cases() -> list[dict]:
    path = COURSE / "dados" / "casos.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@contextmanager
def session(args: argparse.Namespace, *, lab: str) -> Iterator[Any]:
    from langsmith import Client, tracing_context

    configure(args)
    client = Client() if args.send else None
    try:
        with tracing_context(
            enabled=args.send,
            client=client,
            project_name=args.project,
            tags=["estudo", lab],
            metadata={"environment": "lab", "lab": lab, "synthetic": True},
        ):
            yield client
    finally:
        if client is not None:
            client.flush(timeout=10)


def traced_call(client: Any, project: str, name: str, fn: Callable, inputs: dict,
                *, metadata: dict | None = None) -> tuple[dict, str]:
    from langsmith import traceable

    run_id = str(uuid4())
    output = traceable(fn, name=name)(
        inputs, langsmith_extra={"run_id": run_id, "metadata": metadata or {}}
    )
    if client is not None:
        show_trace(client, project, run_id)
    return output, run_id


def show_trace(client: Any, project: str, run_id: str) -> None:
    """URL autenticada obtida do SDK, nunca um link público inventado."""
    from langsmith.utils import LangSmithNotFoundError

    client.flush(timeout=10)
    print(f"run_id: {run_id}")
    for attempt in range(3):
        try:
            run = client.read_run(run_id)
            print(f"Trace: {client.get_run_url(run=run, project_name=project)}")
            return
        except LangSmithNotFoundError:
            time.sleep(0.5 * (attempt + 1))
        except Exception as exc:
            print(f"URL ainda indisponível ({type(exc).__name__}).")
            break
    print(f"Abra https://smith.langchain.com → Tracing → {project}; procure pelo run_id acima.")


def require_real(args: argparse.Namespace) -> None:
    if not args.real:
        raise SystemExit("Este laboratório exige --real para chamar o provedor de modelo.")
    if not os.getenv("LLM_MODEL"):
        raise SystemExit("Defina LLM_MODEL com um modelo disponível na sua conta.")
    provider = os.getenv("LLM_PROVIDER", "openai")
    key = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(provider)
    if key is None or not credential_present(key):
        raise SystemExit("Configure LLM_PROVIDER e a chave correspondente no .env do projeto.")


def real_model():
    from dcra.config import Settings
    from dcra.llm.factory import build_chat_model

    # Modelo e integração que o projeto já usa; sem atualizar dependências.
    return build_chat_model(Settings.from_env())
