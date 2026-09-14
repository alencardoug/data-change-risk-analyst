"""Versão comentada, linha a linha, do laboratório 06 (avaliação/experimentos).

Este arquivo é `06_evaluate_full.py` com explicações didáticas ao lado do
código. A infraestrutura comum já foi explicada em detalhe nos labs 01 e
02 (`01_trace_python_full_explained.py`, `02_dcra_full_explained.py`);
aqui os comentários dessas funções ficam resumidos.

O que este laboratório ensina de novo: o conceito de EXPERIMENTO no
LangSmith — rodar uma função-alvo (`target`) contra TODOS os exemplos de um
dataset (ver lab 05), aplicar um conjunto de "avaliadores" (funções que
comparam a saída obtida com a saída de referência e produzem uma nota) a
cada resultado, e agregar tudo em métricas resumidas. Isso é o que, em
Machine Learning / Engenharia de IA, se chama de "avaliação offline": testar
uma versão do sistema contra casos conhecidos, de forma repetível,
ANTES de colocá-la em produção. O laboratório compara duas variantes do
código do DCRA — "baseline" (correta) e "bug" (com um defeito proposital)
— para mostrar como os avaliadores conseguem DETECTAR essa diferença.
"""

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

# `importlib` é o módulo padrão do Python para trabalhar com importação de
# módulos de forma PROGRAMÁTICA (em vez da palavra-chave `import` fixa no
# código). Usado aqui para importar o laboratório 05 dinamicamente por
# nome, sem criar uma dependência direta no topo do arquivo.
#
# `partial` (de `functools`) cria uma nova função a partir de outra, com
# ALGUNS argumentos já "pré-preenchidos". Explicado com mais detalhe onde é
# usado, em `main()`.
#
# Os avaliadores (funções que dão nota a um resultado) e a função
# `high_risk_recall` (uma métrica agregada específica do DCRA) vêm de um
# módulo separado, `_evaluators.py`, para poderem ser reaproveitados tanto
# aqui (avaliação local) quanto no laboratório de gate de regressão (12).

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
    # Ver explicação linha a linha completa no lab 02. Aqui é usada para
    # anexar, a CADA resultado da avaliação local, um retrato fiel do
    # estado do código no momento em que a avaliação rodou — importante
    # para auditar depois "qual código gerou este número".
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
    # Ver explicação linha a linha completa no lab 02.
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
    comum; este laboratório não chega a chamá-la — `client.evaluate(...)`,
    usado abaixo, já imprime seu próprio nome de experimento, que serve
    como referência para encontrá-lo na UI.)
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
# A PARTIR DAQUI começa a lógica específica deste laboratório (avaliação
# local e via experimentos do LangSmith). Este é o NOVO conteúdo pedagógico.
# ============================================================================

def evaluate_local(cases: list[dict], variant: str) -> dict:
    """Roda a avaliação inteiramente NO SEU COMPUTADOR, sem tocar no
    LangSmith — útil para iterar rápido ou quando não se quer/pode enviar
    dados. É o "modo padrão" quando o script roda sem `--send`.
    """
    # Import local: `target` é a função do DCRA que, dado um `inputs` e uma
    # `variant` ("baseline" ou "bug"), devolve a classificação de risco
    # simulada — o "sistema sob teste" deste laboratório.
    from _dcra import target

    rows = []  # vai acumular um registro por caso avaliado
    for case in cases:
        # Roda o sistema (a variante escolhida) contra os inputs deste caso.
        outputs = target(case["inputs"], variant=variant)

        # Comprehension de dicionário ANINHADA: para cada avaliador `ev` na
        # lista `EVALUATORS`, chama `ev(outputs, case["outputs"])` — cada
        # avaliador é uma função que recebe (resultado obtido, resultado
        # esperado) e devolve um dicionário `{"key": nome_da_metrica,
        # "score": nota}` (ver `_evaluators.py`). A parte
        # `for m in [ev(outputs, case["outputs"])]` é um truque comum para
        # "chamar a função uma vez só e reaproveitar o resultado dentro de
        # uma comprehension": em vez de chamar `ev(...)` duas vezes (uma
        # para pegar `m["key"]`, outra para pegar `m["score"]`), criamos uma
        # lista de UM elemento (`m`) e iteramos sobre ela — assim a chamada
        # acontece só uma vez. O resultado final é um dicionário
        # `{"risk_correct": 1, "review_correct": 0, ...}`, uma entrada por
        # avaliador.
        scores = {m["key"]: m["score"] for ev in EVALUATORS for m in [ev(outputs, case["outputs"]) ]}

        rows.append({"case_id": case["id"], "slice": case["metadata"]["slice"],
                     "outputs": outputs, "reference": case["outputs"], "scores": scores})

    # Para cada avaliador, calcula a MÉDIA de suas notas entre todos os
    # casos. `ev.__name__` é o nome da função Python do avaliador (funções
    # são objetos em Python, e todo objeto de função tem esse atributo
    # embutido) — usado como chave do dicionário de métricas.
    # `sum(r["scores"][ev.__name__] for r in rows) / len(rows)` soma a nota
    # deste avaliador em todas as linhas e divide pelo total de linhas —
    # isto é uma média aritmética simples, escrita com uma "expressão
    # geradora" (a parte `for r in rows` dentro do `sum(...)`, sem
    # colchetes — mais eficiente em memória que criar uma lista intermediária).
    means = {ev.__name__: sum(r["scores"][ev.__name__] for r in rows) / len(rows) for ev in EVALUATORS}

    return {"variant": variant, "n": len(rows), "metrics": means,
            "high_risk_recall": high_risk_recall(rows), "rows": rows, "manifest": manifest()}


def main():
    p = parser(__doc__)
    p.add_argument("--variant", choices=["baseline", "bug", "both"], default="both")
    args = p.parse_args()

    # Decide quais variantes rodar: se o usuário pediu "both", roda as
    # duas; senão, roda só a que foi escolhida. `[args.variant]` cria uma
    # lista de um elemento só, para o `for` mais abaixo funcionar igual nos
    # dois casos (sempre iterando sobre uma lista).
    variants = ["baseline", "bug"] if args.variant == "both" else [args.variant]

    with session(args, lab="06-eval") as client:
        from _dcra import target

        if client:
            # --- Caminho REMOTO: avaliação como Experimento do LangSmith ---
            path = ARTIFACTS / "05-dataset.json"
            if not path.exists():
                raise SystemExit("Execute 05_dataset.py --send antes da avaliação remota.")
            info = json.loads(path.read_text())

            # O comentário abaixo (já existente no laboratório original)
            # explica por que chamamos `publish_dataset` de novo aqui:
            #
            # Valida/reutiliza a versão do arquivo atual antes de fixar o snapshot para ambos.
            #
            # `importlib.import_module("05_dataset")` importa, em tempo de
            # execução, o módulo cujo NOME (como string) é "05_dataset" —
            # equivalente a escrever `import importlib` no topo do arquivo e,
            # em algum ponto do código, um `import 05_dataset` comum (o que
            # não seria válido em Python, já que nomes de módulo não podem
            # começar com dígito ao usar a palavra-chave `import`; por isso
            # a importação dinâmica via `importlib` é necessária aqui).
            # `.publish_dataset(...)` então chama, dentro desse módulo
            # importado, a mesma função explicada em detalhe no
            # `05_dataset_full_explained.py` — o efeito é garantir que o
            # dataset remoto esteja atualizado com o arquivo `casos.jsonl`
            # ATUAL antes de rodar a avaliação, evitando comparar as
            # variantes contra versões diferentes dos dados.
            current = importlib.import_module("05_dataset").publish_dataset(client, read_cases())

            # Se o hash do arquivo atual for diferente do hash salvo em
            # `05-dataset.json` (produzido da última vez que o lab 05 foi
            # rodado com --send), os dados mudaram entre uma execução e
            # outra — pedimos para rodar de novo em vez de seguir com uma
            # comparação que misturaria versões diferentes dos dados.
            if current["source_sha256"] != info["source_sha256"]:
                raise SystemExit("Arquivo de dados mudou. Dataset atualizado; execute este comando de novo.")

            # `client.list_examples(dataset_id=..., as_of=...)` busca os
            # exemplos do dataset EXATAMENTE como estavam no momento
            # `as_of` (o "carimbo de versão" explicado no lab 05) — isso é
            # o que garante que, mesmo se alguém adicionar exemplos depois,
            # este experimento sempre rode contra o mesmo snapshot.
            # `list(...)` converte o iterador devolvido pelo SDK em uma
            # lista Python normal, materializando todos os exemplos de uma vez.
            examples = list(client.list_examples(dataset_id=info["dataset_id"], as_of=info["as_of"]))

            for variant in variants:
                # `partial(target, variant=variant)` cria uma NOVA função
                # que, quando chamada, já chama `target` com `variant`
                # fixado neste valor — só falta fornecer o argumento
                # restante (`inputs`). Isso é necessário porque
                # `client.evaluate(...)` (abaixo) vai chamar essa função
                # sozinho, passando apenas os inputs de cada exemplo — ele
                # não sabe (nem precisa saber) sobre o conceito de
                # "variant", que é específico deste laboratório.
                #
                # `client.evaluate(...)` é o método do SDK que orquestra um
                # EXPERIMENTO completo no LangSmith:
                #   1. para cada exemplo em `data=examples`, chama a função
                #      alvo (`partial(target, variant=variant)`) com o
                #      `inputs` daquele exemplo;
                #   2. registra cada chamada como um run, associado ao
                #      exemplo de origem;
                #   3. aplica cada função em `evaluators=EVALUATORS` sobre
                #      (saída obtida, saída de referência do exemplo),
                #      gravando cada nota como feedback naquele run
                #      (o mesmo mecanismo do lab 04, só que automatizado
                #      em massa);
                #   4. aplica `summary_evaluators=SUMMARY_EVALUATORS` sobre
                #      o conjunto INTEIRO de resultados, para métricas
                #      agregadas (ex.: recall em casos de risco alto);
                #   5. agrupa tudo sob um "experimento" nomeado, visível na
                #      UI do LangSmith lado a lado com outros experimentos
                #      do mesmo dataset — permitindo comparar visualmente
                #      "baseline" vs. "bug".
                #
                #   - experiment_prefix=f"dcra-{variant}": prefixo do nome
                #     do experimento (o LangSmith completa com um sufixo
                #     único automaticamente).
                #   - max_concurrency=1: roda um exemplo de cada vez (sem
                #     paralelismo), para manter a execução simples e
                #     previsível neste laboratório.
                #   - num_repetitions=1: roda cada exemplo uma única vez
                #     (poderia ser mais, para medir variabilidade em
                #     sistemas não-determinísticos, como um LLM real).
                #   - metadata={...}: informações extras anexadas ao
                #     experimento inteiro (não a cada run individual),
                #     úteis para filtrar experimentos na UI depois.
                #   - description="...": texto livre explicando o
                #     propósito deste experimento.
                results = client.evaluate(
                    partial(target, variant=variant), data=examples, evaluators=EVALUATORS,
                    summary_evaluators=SUMMARY_EVALUATORS,
                    experiment_prefix=f"dcra-{variant}", max_concurrency=1, num_repetitions=1,
                    metadata={"variant": variant, "dataset_as_of": info["as_of"],
                              "dataset_sha256": info["source_sha256"], "evaluator_version": "contratos-v1"},
                    description="Grafo real com modelo fixture; mede contratos, não qualidade do LLM.",
                )
                # `client.evaluate(...)` inicia o experimento e devolve
                # imediatamente um objeto que representa o trabalho em
                # andamento. `.wait()` BLOQUEIA a execução do script até
                # que todos os exemplos tenham sido processados — sem essa
                # chamada, o script poderia terminar antes do experimento
                # acabar de rodar no backend.
                results.wait()
                # `results.experiment_name` é o nome final (já com o
                # sufixo único) que o LangSmith deu a este experimento —
                # útil para localizá-lo na UI.
                print(f"Experimento: {results.experiment_name}")
        else:
            # --- Caminho LOCAL: sem nenhuma chamada de rede -----------------
            for variant in variants:
                result = evaluate_local(read_cases(), variant)
                print(variant, result["metrics"], f"recall HIGH={result['high_risk_recall']}")
                write_json(f"06-{variant}.json", result)


if __name__ == "__main__":
    main()
