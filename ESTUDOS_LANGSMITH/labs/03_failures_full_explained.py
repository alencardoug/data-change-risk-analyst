"""Versão comentada, linha a linha, do laboratório 03 (erros e lentidão).

Este arquivo é `03_failures_full.py` com explicações didáticas ao lado do
código. A infraestrutura comum (parser, session, show_trace, write_json
etc.) é idêntica à do laboratório 01 — ver `01_trace_python_full_explained.py`
para a explicação completa dessas partes; aqui os comentários dessas funções
ficam resumidos.

O que este laboratório ensina de novo: como o LangSmith registra um run que
TERMINA COM ERRO (exceção Python não tratada), e como simular retries
(novas tentativas) e degradação controlada (devolver um resultado parcial
em vez de quebrar) — tudo isso SEM depender de derrubar serviços de
verdade: os erros são "injetados" no próprio código Python com
`time.sleep` e `raise`.
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
from langsmith import trace, traceable

# `trace` e `traceable` já foram explicados no lab 01: `trace(...)` abre um
# run manualmente com `with`; `@traceable` transforma uma função inteira em
# um run.

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
    # Ver explicação linha a linha completa no lab 02. (Não é usada de fato
    # por este laboratório, mas faz parte do "kit" de utilidades comuns.)
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

    No SmithDB um run é endereçado por (projeto, trace_id, run_id); `start_time` é opcional e
    acelera a busca. Aqui o run é sempre a raiz, logo trace_id == run_id. Os métodos v2 do SDK
    (`client.runs.*`) são assíncronos: `asyncio.run` executa a corrotina neste script síncrono.

    (Explicação linha a linha completa: ver lab 01.)
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
    # Ver explicação linha a linha completa no lab 02. (Também não é usada
    # de fato aqui — faz parte do kit comum de utilidades.)
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
# A PARTIR DAQUI começa a lógica específica deste laboratório (falhas
# simuladas). Este é o NOVO conteúdo pedagógico do arquivo.
# ============================================================================

# `@traceable(run_type="tool", name="ler_catalogo")`: mesma ideia do lab 01
# — transforma `read_catalog` em uma função que também vira um run "tool"
# no LangSmith. A diferença interessante aqui é que esta função às vezes
# LANÇA UMA EXCEÇÃO (`raise TimeoutError(...)`) — e o LangSmith sabe
# registrar isso também: quando uma função decorada com `@traceable` lança
# um erro, o run correspondente é marcado como "erro" (status de falha) na
# UI, com o traceback (a pilha de chamadas do erro) anexado, em vez de
# "sucesso" com um output normal.
@traceable(run_type="tool", name="ler_catalogo")
def read_catalog(mode: str, attempt: int) -> dict:
    # `time.sleep(segundos)` pausa a execução do programa por aquele tempo.
    # Aqui simulamos uma consulta "lenta" (0.18s) quando `mode == "slow"`,
    # ou "rápida" (0.02s) nos demais casos — só para o trace mostrar
    # diferenças de duração perceptíveis entre execuções.
    time.sleep(0.18 if mode == "slow" else 0.02)

    # `mode in {"fallback", "crash"}` verifica se `mode` é um dos elementos
    # de um CONJUNTO (`set`, delimitado por `{}`) — sets são úteis para
    # testes de pertencimento porque são mais rápidos que listas para isso
    # (embora, com só 2 elementos, a diferença seja irrelevante; é mais uma
    # questão de estilo/idioma Python). A condição completa, unida por
    # `or`, dispara o erro em dois casos:
    #   1. o modo é "fallback" ou "crash" (sempre falha na 1ª tentativa
    #      neste código simplificado, já que a função só é chamada de novo
    #      via retry em `pipeline`, abaixo)
    #   2. o modo é "retry" E esta é a primeira tentativa (`attempt == 1`)
    #      — ou seja, "retry" falha uma vez e depois funciona.
    if mode in {"fallback", "crash"} or (mode == "retry" and attempt == 1):
        # `raise TimeoutError("mensagem")` cria e lança uma exceção do tipo
        # `TimeoutError` (uma classe de exceção padrão do Python, normalmente
        # usada para erros de tempo esgotado em operações de rede/IO — aqui
        # é usada só simbolicamente, para representar "o catálogo demorou
        # demais e desistimos"). Lançar uma exceção interrompe IMEDIATAMENTE
        # a execução normal da função; o controle "salta" para o primeiro
        # bloco `except` compatível, na função que chamou esta (`pipeline`).
        raise TimeoutError("timeout sintético do laboratório")

    # Se não caiu no `if` acima, a "consulta" foi bem-sucedida.
    return {"dependency_count": 2, "status": "OBTAINED"}


def pipeline(inputs: dict) -> dict:
    """Implementa uma política simples de retry: tenta `read_catalog` até
    2 vezes; se a segunda tentativa também falhar, decide entre "desistir
    com erro" (cenário `crash`) ou "devolver uma resposta degradada, mas
    utilizável" (demais cenários).
    """
    # `range(1, 3)` gera os números 1 e 2 (o limite superior, 3, NÃO é
    # incluído — comportamento padrão de `range` em Python). Ou seja, esta
    # função tenta no máximo 2 vezes.
    for attempt in range(1, 3):
        try:
            result = read_catalog(inputs["mode"], attempt)
            # Se a chamada acima NÃO lançou exceção, já temos o resultado:
            # `result | {...}` mescla o dicionário devolvido com informações
            # extras sobre a tentativa, e a função retorna imediatamente
            # (o `for` nem chega à segunda iteração).
            return result | {"attempts": attempt, "degraded": False}
        except TimeoutError:
            # Só entramos aqui se `read_catalog` lançou `TimeoutError`.
            # Se esta foi a ÚLTIMA tentativa permitida (`attempt == 2`):
            if attempt == 2:
                # No cenário "crash", desistimos de verdade: `raise` sem
                # argumento, dentro de um bloco `except`, RELANÇA a MESMA
                # exceção que acabamos de capturar (preservando o
                # traceback original) — ou seja, propaga o erro para quem
                # chamou `pipeline`, em vez de escondê-lo.
                if inputs["mode"] == "crash":
                    raise
                # Nos demais cenários (ex.: "fallback"), em vez de propagar
                # o erro, devolvemos um resultado "degradado": ainda é uma
                # resposta válida (um dicionário), só que sinalizando que o
                # catálogo não pôde ser obtido. Essa é uma estratégia comum
                # em sistemas de produção: preferir uma resposta parcial e
                # sinalizada a quebrar tudo.
                return {"status": "UNAVAILABLE", "dependency_count": None,
                        "attempts": attempt, "degraded": True}
            # Se ainda não foi a última tentativa (attempt == 1), o `for`
            # simplesmente continua para a próxima iteração (attempt == 2)
            # e tenta de novo — não precisamos escrever nada explícito
            # aqui para isso acontecer; é o comportamento natural do laço.

    # Esta linha só existiria se o `for` terminasse sem nenhum `return` nem
    # `raise` — o que, pela lógica acima, é matematicamente impossível
    # (toda combinação de `attempt` e resultado leva a um `return` ou
    # `raise`). `AssertionError("inalcançável")` é uma forma de dizer "se
    # você chegou aqui, há um bug na minha lógica" — uma rede de segurança
    # para o programador, não um caminho esperado de execução.
    raise AssertionError("inalcançável")


def main():
    args = parser(__doc__).parse_args()
    rows = []  # lista que vai acumular um resumo de cada modo testado
    with session(args, lab="03-falhas") as client:
        # Percorre, em ordem, os quatro modos de falha simulados.
        for mode in ["slow", "retry", "fallback", "crash"]:
            # `time.perf_counter()` é um cronômetro de alta precisão
            # (melhor que `time.time()` para medir DURAÇÕES curtas, porque
            # não é afetado por ajustes do relógio do sistema).
            start = time.perf_counter()
            try:
                # `with trace(...) as run:` abre um run raiz manualmente
                # (mesma ideia do lab 01), um para cada modo testado.
                # O comentário abaixo (que já existia no lab original)
                # explica o comportamento mais importante desta seção:
                #
                # A exceção atravessa o `with`: o run raiz é fechado com o erro e só então chega aqui.
                #
                # Ou seja: se `pipeline(...)` lançar uma exceção (caso
                # "crash", na 2ª tentativa), o gerenciador de contexto do
                # `trace(...)` INTERCEPTA essa exceção antes de propagá-la
                # adiante: ele marca o run como "erro" no LangSmith
                # (registrando o traceback), FECHA o run automaticamente, e
                # só DEPOIS deixa a exceção continuar se propagando para o
                # `except TimeoutError:` logo abaixo. Não precisamos chamar
                # `run.end(...)` manualmente no caminho de erro — o `with`
                # cuida disso sozinho quando algo dá errado dentro dele.
                with trace(f"falha-{mode}", inputs={"mode": mode}, metadata={"scenario": mode}) as run:
                    output = pipeline({"mode": mode})
                    # Este `run.end(outputs=output)` só é alcançado quando
                    # `pipeline` NÃO lançou exceção (ou seja, em todos os
                    # modos exceto "crash").
                    run.end(outputs=output)
            except TimeoutError:
                # Chega aqui apenas no modo "crash", depois que o `with
                # trace(...)` já fechou o run como erro. Aqui só definimos
                # uma variável Python local `output` para as próximas
                # linhas (impressão e registro) terem algo consistente
                # para mostrar — isso não afeta o que já foi gravado no
                # LangSmith, que é o traceback real do erro.
                output = {"error": "TimeoutError", "expected": True}

            # `round(numero, 3)` arredonda para 3 casas decimais, só para a
            # impressão ficar mais limpa (ex.: 0.183 em vez de 0.182731...).
            elapsed = round(time.perf_counter() - start, 3)

            # `run.id` continua acessível mesmo depois que o bloco `with`
            # terminou (com ou sem erro) — o objeto `run` não "desaparece"
            # ao sair do `with`, só o comportamento de fechamento
            # automático é que já foi executado.
            rows.append({"mode": mode, "seconds": elapsed, "outputs": output, "run_id": str(run.id)})
            print(mode, output, f"{elapsed}s")
            if client:
                show_trace(client, args.project, str(run.id), start_time=run.start_time)

    # Este `write_json` fica FORA do `with session(...)`, de propósito:
    # salvar o arquivo local não depende de a sessão de tracing ainda estar
    # aberta (mas repare que isso é uma escolha de estilo do laboratório
    # original — funcionalmente também funcionaria dentro do `with`).
    write_json("03-falhas.json", rows)


if __name__ == "__main__":
    main()
