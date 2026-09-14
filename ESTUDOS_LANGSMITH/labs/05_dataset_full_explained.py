"""Versão comentada, linha a linha, do laboratório 05 (criar/reutilizar um dataset).

Este arquivo é `05_dataset_full.py` com explicações didáticas ao lado do
código. A infraestrutura comum já foi explicada em detalhe nos labs 01 e
02 (`01_trace_python_full_explained.py`, `02_dcra_full_explained.py`);
aqui os comentários dessas funções ficam resumidos.

O que este laboratório ensina de novo: o conceito de DATASET no LangSmith —
uma coleção nomeada e versionada de "exemplos" (pares input/output de
referência), usada depois para rodar EXPERIMENTOS de avaliação (ver lab 06)
de forma repetível. Também mostra uma técnica de idempotência: nomear o
dataset com um hash do arquivo de origem, para nunca publicar duas vezes a
mesma versão dos dados por engano, e para detectar com segurança quando o
dataset remoto foi alterado por fora (o que aqui é tratado como erro, não
como algo para sobrescrever silenciosamente).
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
from uuid import NAMESPACE_URL, uuid5

from dotenv import load_dotenv

# `NAMESPACE_URL` é um UUID fixo e padronizado, definido pela própria
# especificação de UUIDs (RFC 4122), usado como "espaço de nomes" base.
# `uuid5(namespace, texto)` gera um UUID DETERMINÍSTICO: o mesmo par
# (namespace, texto) sempre produz exatamente o mesmo UUID, em qualquer
# computador, a qualquer momento — diferente de `uuid4()` (lab 02), que é
# aleatório a cada chamada. Isso é essencial aqui: queremos que o MESMO
# caso de teste sempre gere o MESMO id de exemplo no dataset, para que
# rodar o script de novo "atualize" o exemplo existente em vez de duplicá-lo.

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
    # Ver explicação linha a linha completa no lab 02. Este laboratório usa
    # `digest` diretamente em `publish_dataset` abaixo, para descobrir se o
    # arquivo `casos.jsonl` mudou desde a última publicação.
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest() -> dict[str, Any]:
    # Ver explicação linha a linha completa no lab 02. (Não usada de fato
    # neste laboratório; faz parte do kit comum de utilidades.)
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
    # Ver explicação linha a linha completa no lab 02. Aqui SIM é usada de
    # verdade: cada "caso" lido deste arquivo vira um exemplo do dataset.
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
    """Ver explicação linha a linha completa no lab 01. (Faz parte do kit
    comum; este laboratório específico não chega a chamá-la, pois não cria
    runs de tracing — ele trabalha diretamente com a API de Datasets.)
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
# A PARTIR DAQUI começa a lógica específica deste laboratório (criar ou
# reutilizar um dataset no LangSmith). Este é o NOVO conteúdo pedagógico.
# ============================================================================

def publish_dataset(client, cases: list[dict], *, data_path=None,
                    prefix: str = "dcra-estudo-contratos", artifact: str = "05-dataset.json") -> dict:
    """Cria (na primeira vez) ou reaproveita (nas vezes seguintes) um
    dataset no LangSmith, cujo nome incorpora um hash do arquivo de dados
    local. Isso implementa uma forma simples e robusta de "versionamento por
    conteúdo": se o arquivo `casos.jsonl` mudar, o hash muda, e portanto o
    NOME do dataset muda — nunca vamos, sem querer, misturar exemplos de
    duas versões diferentes dos dados dentro do mesmo dataset remoto.

    `client` não tem anotação de tipo aqui (ao contrário de outras funções
    deste arquivo) — em Python isso é permitido; simplesmente significa
    "aceita qualquer tipo", sem checagem estática. `data_path=None` e os
    demais parâmetros depois do `*` são parâmetros NOMEADOS com valor
    padrão: quem chama pode omiti-los (como faz `main()`, mais abaixo) ou
    sobrescrevê-los quando quiser (como faz o lab 06, passando outro valor).
    """
    # Import local: estas duas exceções específicas do LangSmith só
    # interessam dentro desta função.
    #   - LangSmithNotFoundError: "não existe um dataset com este nome ainda"
    #   - LangSmithConflictError: "duas execuções tentaram criar o mesmo
    #     dataset ao mesmo tempo, e outra já venceu a corrida" (uma
    #     condição de corrida / race condition)
    from langsmith.utils import LangSmithConflictError, LangSmithNotFoundError

    # `data_path or (COURSE / "dados" / "casos.jsonl")`: se `data_path` foi
    # passado pelo chamador, usa-o; senão (`None` é "falsy"), usa o caminho
    # padrão do arquivo de casos do curso. Calcula o hash SHA-256 desse
    # arquivo (ver `digest`, explicada no lab 02).
    fingerprint = digest(data_path or (COURSE / "dados" / "casos.jsonl"))

    # `fingerprint[:12]`: "fatiamento" (slicing) de string — pega só os 12
    # primeiros caracteres do hash completo (que tem 64 caracteres), só
    # para o nome do dataset ficar mais curto e ainda assim praticamente
    # único. O nome final fica algo como "dcra-estudo-contratos-a1b2c3d4e5f6".
    name = f"{prefix}-{fingerprint[:12]}"

    try:
        # Tenta LER (não criar) um dataset já existente com esse nome exato.
        ds = client.read_dataset(dataset_name=name)
    except LangSmithNotFoundError:
        # Se não existir ainda, tenta CRIAR.
        try:
            ds = client.create_dataset(name, description="Casos sintéticos do curso; gabarito manual.",
                                       metadata={"source_sha256": fingerprint})
        except LangSmithConflictError:
            # Se, entre a tentativa de leitura (que falhou) e a tentativa
            # de criação (que também falhou, porque alguém criou primeiro),
            # outra execução concorrente já tiver criado o dataset, apenas
            # o lemos agora que ele existe. Este padrão "tentar ler, se não
            # existir tentar criar, se der conflito ler de novo" é uma
            # forma clássica e segura de lidar com condições de corrida
            # sem precisar de um mecanismo de trava (lock) externo.
            ds = client.read_dataset(dataset_name=name)

    # List comprehension que constrói a lista de "exemplos" a partir dos
    # casos lidos do arquivo local. Para cada `case` em `cases`, monta um
    # dicionário com:
    examples = [{
        # `uuid5(NAMESPACE_URL, texto)` gera um UUID determinístico (ver
        # explicação do import, no topo do arquivo) a partir de uma string
        # única por caso: o nome do dataset + o id do caso local
        # (`case['id']`). Assim, mesmo rodando o script várias vezes, o
        # MESMO caso sempre recebe o MESMO id de exemplo no LangSmith —
        # essencial para o mecanismo de "atualizar em vez de duplicar" logo
        # abaixo.
        "id": str(uuid5(NAMESPACE_URL, f"{name}/{case['id']}")),
        "inputs": case["inputs"], "outputs": case["outputs"],
        # `case["metadata"] | {"case_id": case["id"]}`: mescla (operador
        # `|` entre dicionários) os metadados originais do caso com um
        # campo extra `case_id`, para facilitar rastrear de qual caso
        # local cada exemplo remoto veio.
        "metadata": case["metadata"] | {"case_id": case["id"]},
    } for case in cases]

    # Busca TODOS os exemplos que já existem no dataset remoto, e monta um
    # dicionário `{id_do_exemplo: objeto_exemplo}` para consultas rápidas
    # por id (em vez de percorrer uma lista toda vez).
    existing = {str(e.id): e for e in client.list_examples(dataset_id=ds.id)}

    # `{e["id"] for e in examples}` é uma COMPREHENSION DE CONJUNTO (set
    # comprehension) — mesma ideia de uma list comprehension, mas o
    # resultado é um `set` (sem duplicatas, sem ordem garantida). Aqui
    # reúne todos os ids de exemplo que DEVERIAM existir, segundo os dados
    # locais atuais.
    expected_ids = {e["id"] for e in examples}

    # `set(existing)` cria um conjunto com as CHAVES do dicionário
    # `existing` (os ids que já existem no remoto). O operador `-` entre
    # conjuntos é "diferença": produz os elementos que estão no primeiro
    # conjunto mas NÃO no segundo. Ou seja: `set(existing) - expected_ids`
    # é "ids que existem no dataset remoto, mas que os dados locais atuais
    # não esperam mais". Se essa diferença não for vazia, alguém adicionou
    # exemplos extras diretamente no LangSmith (fora deste script) — o
    # laboratório trata isso como um erro, para nunca publicar por cima de
    # um dataset que foi editado manualmente por outra pessoa/processo.
    if set(existing) - expected_ids:
        raise SystemExit("Dataset remoto tem casos extras. Use uma nova versão local; não sobrescreva.")

    # Verifica, exemplo a exemplo, se algum já existente no remoto tem
    # `inputs`/`outputs` DIFERENTES do que os dados locais esperam agora
    # (o que indicaria uma edição manual do exemplo, não coberta pelo
    # hash do arquivo local — por exemplo, se alguém corrigiu um exemplo
    # direto na UI do LangSmith).
    for item in examples:
        # `.get(chave)` num dicionário devolve `None` se a chave não
        # existir, em vez de lançar erro — diferente de `dicionario[chave]`.
        previous = existing.get(item["id"])
        if previous and (previous.inputs != item["inputs"] or previous.outputs != item["outputs"]):
            raise SystemExit("Dataset remoto foi editado. Não vou misturar versões diferentes.")

    # Lista dos exemplos que AINDA NÃO existem no remoto (seus ids não
    # estão em `existing`) — são os que precisam ser criados agora.
    missing = [item for item in examples if item["id"] not in existing]
    if missing:
        # Envia todos de uma vez (mais eficiente do que um por um).
        client.create_examples(dataset_id=ds.id, examples=missing)

    # O comentário abaixo (já existente no laboratório original) explica um
    # conceito central de reprodutibilidade em datasets do LangSmith:
    #
    # A versão "latest" vira o carimbo `as_of` que fixa o snapshot usado pelos experimentos.
    #
    # Um dataset no LangSmith pode ser editado ao longo do tempo (novos
    # exemplos, exemplos corrigidos). `read_dataset_version(dataset_id, tag="latest")`
    # pergunta: "qual o carimbo de tempo (timestamp) da versão mais recente
    # deste dataset AGORA?". Esse `as_of` (um objeto `datetime`) pode depois
    # ser usado para "congelar" um snapshot exato do dataset — mesmo que
    # alguém adicione mais exemplos depois, um experimento que referencia
    # este `as_of` sempre vai rodar contra o dataset EXATAMENTE como ele
    # estava neste instante. Isso é o que garante comparações justas entre
    # experimentos (ver lab 06).
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
    # `cases[0]`: acessa o PRIMEIRO elemento da lista (índices em Python
    # começam em 0), só para dar ao usuário um exemplo concreto do formato
    # dos dados no terminal.
    print(cases[0])

    with session(args, lab="05-dataset") as client:
        if client:
            # Só publica de verdade no LangSmith se `--send` foi passado.
            publish_dataset(client, cases)
        else:
            # Em modo local (sem --send), o laboratório só mostra os dados
            # que SERIAM publicados, sem fazer nenhuma chamada de rede.
            print("Modo local: nenhum dataset remoto criado. Use --send para publicar os casos sintéticos.")


if __name__ == "__main__":
    main()
