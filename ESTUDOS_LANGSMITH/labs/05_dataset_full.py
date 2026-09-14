"""Cria/reutiliza dataset de estudo identificado pelo hash do arquivo local."""

import argparse
import asyncio
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

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


def show_trace(client: Any, project: str, run_id: str, *, start_time: datetime | None = None) -> None:
    """URL autenticada do run, pedida ao endpoint v2 do LangSmith; nunca um link montado à mão.

    No SmithDB um run é endereçado por (projeto, trace_id, run_id); `start_time` é opcional e
    acelera a busca. Aqui o run é sempre a raiz, logo trace_id == run_id. Os métodos v2 do SDK
    (`client.runs.*`) são assíncronos: `asyncio.run` executa a corrotina neste script síncrono.
    """
    from langsmith import NotFoundError
    from langsmith.utils import LangSmithNotFoundError

    client.flush(timeout=10)
    print(f"run_id: {run_id}")
    for attempt in range(3):  # o projeto e o run podem levar instantes para ficar consultáveis
        try:
            project_id = str(client.read_project(project_name=project).id)
            response = asyncio.run(client.runs.get_url(
                run_id, project_id=project_id, trace_id=run_id, start_time=start_time))
            if response.url:
                print(f"Trace: {response.url}")
                return
            time.sleep(0.5 * (attempt + 1))
        except (LangSmithNotFoundError, NotFoundError):
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



def publish_dataset(client, cases: list[dict], *, data_path=None,
                    prefix: str = "dcra-estudo-contratos", artifact: str = "05-dataset.json") -> dict:
    from langsmith.utils import LangSmithConflictError, LangSmithNotFoundError

    fingerprint = digest(data_path or (COURSE / "dados" / "casos.jsonl"))
    name = f"{prefix}-{fingerprint[:12]}"
    try:
        ds = client.read_dataset(dataset_name=name)
    except LangSmithNotFoundError:
        try:
            ds = client.create_dataset(name, description="Casos sintéticos do curso; gabarito manual.",
                                       metadata={"source_sha256": fingerprint})
        except LangSmithConflictError:
            ds = client.read_dataset(dataset_name=name)
    examples = [{
        "id": str(uuid5(NAMESPACE_URL, f"{name}/{case['id']}")),
        "inputs": case["inputs"], "outputs": case["outputs"],
        "metadata": case["metadata"] | {"case_id": case["id"]},
    } for case in cases]
    existing = {str(e.id): e for e in client.list_examples(dataset_id=ds.id)}
    expected_ids = {e["id"] for e in examples}
    if set(existing) - expected_ids:
        raise SystemExit("Dataset remoto tem casos extras. Use uma nova versão local; não sobrescreva.")
    for item in examples:
        previous = existing.get(item["id"])
        if previous and (previous.inputs != item["inputs"] or previous.outputs != item["outputs"]):
            raise SystemExit("Dataset remoto foi editado. Não vou misturar versões diferentes.")
    missing = [item for item in examples if item["id"] not in existing]
    if missing:
        client.create_examples(dataset_id=ds.id, examples=missing)
    # A versão "latest" vira o carimbo `as_of` que fixa o snapshot usado pelos experimentos.
    dataset_version = client.read_dataset_version(dataset_id=ds.id, tag="latest")
    info = {"dataset_name": name, "dataset_id": str(ds.id), "source_sha256": fingerprint,
            "as_of": dataset_version.as_of.isoformat(), "examples": len(examples)}
    write_json(artifact, info)
    print(f"Abra https://smith.langchain.com → Datasets & Experiments → {name}")
    return info


def main():
    args = parser(__doc__).parse_args()
    cases = read_cases()
    print(f"{len(cases)} casos: inputs, outputs de referência e metadata.")
    print(cases[0])
    with session(args, lab="05-dataset") as client:
        if client:
            publish_dataset(client, cases)
        else:
            print("Modo local: nenhum dataset remoto criado. Use --send para publicar os casos sintéticos.")


if __name__ == "__main__":
    main()
