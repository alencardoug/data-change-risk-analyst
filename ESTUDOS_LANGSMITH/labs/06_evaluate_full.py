"""Compara baseline e bug localmente ou como experimentos no LangSmith."""

import argparse
import asyncio
import hashlib
import importlib
import json
import os
import platform
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from functools import partial
from importlib.metadata import version
from pathlib import Path
from typing import Any

from _evaluators import EVALUATORS, SUMMARY_EVALUATORS, high_risk_recall
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


def evaluate_local(cases: list[dict], variant: str) -> dict:
    from _dcra import target

    rows = []
    for case in cases:
        outputs = target(case["inputs"], variant=variant)
        scores = {m["key"]: m["score"] for ev in EVALUATORS for m in [ev(outputs, case["outputs"]) ]}
        rows.append({"case_id": case["id"], "slice": case["metadata"]["slice"],
                     "outputs": outputs, "reference": case["outputs"], "scores": scores})
    means = {ev.__name__: sum(r["scores"][ev.__name__] for r in rows) / len(rows) for ev in EVALUATORS}
    return {"variant": variant, "n": len(rows), "metrics": means,
            "high_risk_recall": high_risk_recall(rows), "rows": rows, "manifest": manifest()}


def main():
    p = parser(__doc__)
    p.add_argument("--variant", choices=["baseline", "bug", "both"], default="both")
    args = p.parse_args()
    variants = ["baseline", "bug"] if args.variant == "both" else [args.variant]
    with session(args, lab="06-eval") as client:
        from _dcra import target

        if client:
            path = ARTIFACTS / "05-dataset.json"
            if not path.exists():
                raise SystemExit("Execute 05_dataset.py --send antes da avaliação remota.")
            info = json.loads(path.read_text())
            # Valida/reutiliza a versão do arquivo atual antes de fixar o snapshot para ambos.
            current = importlib.import_module("05_dataset").publish_dataset(client, read_cases())
            if current["source_sha256"] != info["source_sha256"]:
                raise SystemExit("Arquivo de dados mudou. Dataset atualizado; execute este comando de novo.")
            examples = list(client.list_examples(dataset_id=info["dataset_id"], as_of=info["as_of"]))
            for variant in variants:
                results = client.evaluate(
                    partial(target, variant=variant), data=examples, evaluators=EVALUATORS,
                    summary_evaluators=SUMMARY_EVALUATORS,
                    experiment_prefix=f"dcra-{variant}", max_concurrency=1, num_repetitions=1,
                    metadata={"variant": variant, "dataset_as_of": info["as_of"],
                              "dataset_sha256": info["source_sha256"], "evaluator_version": "contratos-v1"},
                    description="Grafo real com modelo fixture; mede contratos, não qualidade do LLM.",
                )
                results.wait()
                print(f"Experimento: {results.experiment_name}")
        else:
            for variant in variants:
                result = evaluate_local(read_cases(), variant)
                print(variant, result["metrics"], f"recall HIGH={result['high_risk_recall']}")
                write_json(f"06-{variant}.json", result)


if __name__ == "__main__":
    main()
