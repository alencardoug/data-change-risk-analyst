"""Trace de Python puro: raiz + duas etapas, sem LangChain e sem modelo.

Versão autocontida do lab 01: mesma lógica de `01_trace_python.py`, mas com a
infraestrutura de `_common.py` inline, sem `from _common import ...`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langsmith import trace, traceable

COURSE = Path(__file__).resolve().parents[1]
ROOT = COURSE.parent
ARTIFACTS = COURSE / "artefatos"


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


def write_json(name: str, value: Any) -> Path:
    ARTIFACTS.mkdir(exist_ok=True)
    path = ARTIFACTS / name
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")
    print(f"Arquivo: {path.relative_to(ROOT)}")
    return path


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


@traceable(run_type="tool", name="consultar_cardapio")
def menu(item: str) -> dict:
    return {"item": item, "preco_reais": 18, "disponivel": True}


@traceable(name="calcular_total")
def total(price: int, quantity: int) -> int:
    return price * quantity


def order(inputs: dict) -> dict:
    item = menu(inputs["item"])
    return {"total_reais": total(item["preco_reais"], inputs["quantidade"]), "moeda": "BRL"}


def main():
    args = parser(__doc__).parse_args()
    inputs = {"item": "risoto-de-dados", "quantidade": 2}
    with session(args, lab="01-python") as client:
        # `trace` abre o run raiz; as funções @traceable chamadas aqui dentro viram filhas dele.
        with trace("pedido-restaurante", inputs=inputs, metadata={"scenario": "pedido-valido"}) as run:
            result = order(inputs)
            run.end(outputs=result)
        if client:
            show_trace(client, args.project, str(run.id), start_time=run.start_time)
        print(result)
        # Endereço completo do run (projeto + start_time + id): o lab 04 precisa dele para anexar feedback.
        write_json("01-trace.json", {"outputs": result, "run_id": str(run.id), "project": args.project,
                                     "start_time": run.start_time.isoformat(), "sent": args.send})


if __name__ == "__main__":
    main()
