"""Versão comentada, linha a linha, do laboratório 04 (feedback via API).

Este arquivo é `04_feedback_full.py` com explicações didáticas ao lado do
código. A infraestrutura comum já foi explicada em detalhe em
`01_trace_python_full_explained.py` (parser, session, show_trace,
write_json) e em `02_dcra_full_explained.py` (digest, manifest); aqui os
comentários dessas funções ficam resumidos.

O que este laboratório ensina de novo: o conceito de FEEDBACK no LangSmith
— uma nota (score) e/ou comentário anexados a um run JÁ EXISTENTE, depois
que ele foi criado. Diferente de `inputs`/`outputs` (que descrevem O QUE a
função fez), feedback descreve uma AVALIAÇÃO sobre esse run — pode vir de
um humano (via UI) ou, como aqui, de código automatizado que checa um
critério objetivo (`feedback_source_type="api"`).

Pré-requisito para rodar de verdade: é preciso já ter executado
`01_trace_python_full.py --send` (ou a versão sem "_full"), porque este
laboratório LÊ o arquivo `artefatos/01-trace.json` que aquele laboratório
produziu, para saber a qual run anexar o feedback.
"""

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

from dotenv import load_dotenv

COURSE = Path(__file__).resolve().parents[1]
ROOT = COURSE.parent
ARTIFACTS = COURSE / "artefatos"
sys.path.insert(0, str(ROOT / "src"))


def parser(description: str) -> argparse.ArgumentParser:
    # Ver explicação linha a linha completa no lab 01.
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--send", action="store_true", help="Envia dados sintéticos ao seu LangSmith.")
    p.add_argument("--project", default=os.getenv("DCRA_LAB_PROJECT", "dcra-estudos"))
    return p


def configure(args: argparse.Namespace) -> None:
    # Ver explicação linha a linha completa no lab 01.
    enabled = "true" if args.send else "false"
    os.environ["LANGSMITH_TRACING"] = enabled
    os.environ["LANGCHAIN_TRACING_V2"] = enabled
    load_dotenv(ROOT / ".env", override=False)
    os.environ["LANGSMITH_PROJECT"] = args.project
    if args.send and not credential_present("LANGSMITH_API_KEY"):
        raise SystemExit("Preencha LANGSMITH_API_KEY em .env para usar --send. Veja 03-preparacao.md.")


def credential_present(name: str) -> bool:
    # Ver explicação linha a linha completa no lab 01.
    value = os.getenv(name, "").strip()
    return bool(value and "..." not in value and not value.startswith("<"))


def digest(path: Path) -> str:
    # Ver explicação linha a linha completa no lab 02.
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest() -> dict[str, Any]:
    # Ver explicação linha a linha completa no lab 02.
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
    # Ver explicação linha a linha completa no lab 01.
    ARTIFACTS.mkdir(exist_ok=True)
    path = ARTIFACTS / name
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")
    print(f"Arquivo: {path.relative_to(ROOT)}")
    return path


def read_cases() -> list[dict]:
    # Ver explicação linha a linha completa no lab 02. (Não usada de fato
    # neste laboratório; faz parte do kit comum de utilidades.)
    path = COURSE / "dados" / "casos.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@contextmanager
def session(args: argparse.Namespace, *, lab: str) -> Iterator[Any]:
    # Ver explicação linha a linha completa no lab 01.
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

    (Explicação linha a linha completa: ver lab 01. Esta função existe no
    "kit" comum de utilidades, mas repare que este laboratório específico
    não chega a chamá-la — ele usa `client.create_feedback` diretamente,
    ver `main()` abaixo.)
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
    # Ver explicação linha a linha completa no lab 02. (Não usada de fato
    # neste laboratório; faz parte do kit comum de utilidades.)
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


# ============================================================================
# A PARTIR DAQUI começa a lógica específica deste laboratório (anexar
# feedback a um run já existente). Este é o NOVO conteúdo pedagógico.
# ============================================================================

def main():
    args = parser(__doc__).parse_args()

    # Monta o caminho do arquivo produzido pelo laboratório 01
    # (`.../artefatos/01-trace.json`) e verifica se ele existe.
    path = ARTIFACTS / "01-trace.json"
    if not path.exists():
        # Sem esse arquivo, não temos como saber qual run anotar — o
        # script para aqui com uma instrução clara do que fazer antes.
        raise SystemExit("Execute primeiro 01_trace_python.py (com --send se quiser anexar feedback remoto).")

    # `json.loads(texto)` faz o caminho inverso de `json.dumps`: converte
    # um texto JSON de volta para estruturas Python (aqui, um dicionário).
    saved = json.loads(path.read_text())

    # Este é o "critério objetivo" deste laboratório: o pedido do lab 01
    # era 2 unidades a R$18 cada, então o total esperado é R$36. `int(...)`
    # aplicado a uma comparação booleana converte True→1 e False→0 — um
    # jeito comum de transformar um "sim/não" em uma nota numérica simples
    # (aqui, 0 ou 1) para o feedback do LangSmith, que espera um `score`
    # numérico.
    score = int(saved["outputs"]["total_reais"] == 36)
    print(f"lab_total_correto={score}; origem=API/código, não anotação humana")

    with session(args, lab="04-feedback") as client:
        # Só tenta anexar feedback de verdade se `--send` foi passado (ou
        # seja, se existe uma conexão de fato com o LangSmith).
        if client:
            # Só faz sentido anexar feedback REMOTO se o trace do lab 01
            # também tiver sido enviado (`saved["sent"]`) e se tivermos
            # salvo o horário de início do run (`"start_time" in saved`,
            # que verifica se essa CHAVE existe no dicionário).
            if not saved["sent"] or "start_time" not in saved:
                raise SystemExit("O trace salvo é local ou antigo. Rode 01_trace_python.py --send primeiro.")

            # O comentário abaixo (já existente no laboratório original)
            # explica por que buscamos o projeto antes de criar o feedback:
            #
            # O run é localizado pelo projeto (session_id) e pela hora de início, não só pelo id.
            #
            # No LangSmith (API v2 / SmithDB), localizar um run de forma
            # eficiente exige saber em qual projeto ele está — por isso lemos
            # o objeto `project` a partir do nome salvo, para obter seu `id`
            # (que a API chama de `session_id` neste contexto de feedback,
            # por razões históricas do produto).
            project = client.read_project(project_name=saved["project"])

            # `client.create_feedback(...)` é o método do SDK do LangSmith
            # que cria uma nova entrada de FEEDBACK associada a um run:
            #   - saved["run_id"]: o ID do run que estamos avaliando (o
            #     primeiro argumento posicional do método).
            #   - key="lab_total_correto": o "nome" desta métrica de
            #     feedback (pode haver várias métricas diferentes no mesmo
            #     run, cada uma com sua própria `key`).
            #   - score=score: o valor numérico da avaliação (aqui, 0 ou 1).
            #   - comment="...": um texto livre explicando o critério usado
            #     (aparece na UI ao lado da nota).
            #   - feedback_source_type="api": informa ao LangSmith que este
            #     feedback foi gerado por CÓDIGO automatizado (via API), não
            #     por um humano clicando na interface — a UI mostra essa
            #     origem de forma diferente (ícone/rótulo distintos).
            #   - session_id=project.id: o ID do projeto (ver comentário
            #     acima sobre por que isso é necessário para localizar o run).
            #   - trace_id=saved["run_id"]: como este run é sempre a RAIZ de
            #     seu próprio trace (não tem "pai"), o id do trace é igual ao
            #     id do run — por isso o comentário original diz "raiz:
            #     trace_id == run_id".
            #   - start_time=datetime.fromisoformat(saved["start_time"]):
            #     `datetime.fromisoformat(texto)` faz o caminho inverso de
            #     `.isoformat()` (usado no lab 01 para salvar a data como
            #     texto): reconstrói um objeto `datetime` Python a partir da
            #     string ISO-8601 salva no JSON. Passar isso acelera a
            #     localização do run no backend (evita uma varredura ampla
            #     por tempo).
            feedback = client.create_feedback(
                saved["run_id"], key="lab_total_correto", score=score,
                comment="Critério sintético: dois itens de R$18 devem somar R$36.",
                feedback_source_type="api",
                session_id=project.id, trace_id=saved["run_id"],  # raiz: trace_id == run_id
                start_time=datetime.fromisoformat(saved["start_time"]),
            )
            # `feedback.id` é o identificador da entrada de feedback recém
            # criada (diferente do `run_id`!). Imprimimos para confirmar o
            # sucesso da operação e orientar o usuário a conferir na UI.
            print(f"Feedback criado: {feedback.id}. Abra o trace do laboratório 01.")


if __name__ == "__main__":
    main()
