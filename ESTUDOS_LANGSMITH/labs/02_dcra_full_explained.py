"""Versão comentada, linha a linha, do laboratório 02 (grafo real do DCRA).

Este arquivo é `02_dcra_full.py` com explicações didáticas ao lado do
código. A infraestrutura comum (parser, session, show_trace, write_json,
etc.) é IDÊNTICA à do laboratório 01 e já foi comentada em detalhe em
`01_trace_python_full_explained.py` — aqui os comentários dessas funções
ficam mais curtos (para não repetir o mesmo texto seis vezes) e apontam de
volta para o arquivo 01 quando fizer sentido. O foco deste arquivo é
explicar o que é NOVO aqui: rodar um GRAFO de verdade (LangGraph) dentro de
um `tracing_context`, pausas de "human-in-the-loop" (interrupções que
esperam uma decisão humana) e como o LangSmith organiza múltiplos runs raiz
que compartilham o mesmo `thread_id`.

Contexto de negócio: "DCRA" é o sistema de avaliação de risco de mudanças de
schema de banco de dados que este projeto implementa (ver README do
repositório). Este laboratório roda o grafo real do DCRA contra um catálogo
fixture (dados de mentira, sem banco de verdade) para observar o trace
completo: classificação de risco, pontos de pausa para revisão humana, e
retomada da execução depois de uma decisão (aprovar/rejeitar/devolver).
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
from uuid import uuid4

from dotenv import load_dotenv

# --- Imports -----------------------------------------------------------
# `uuid4()` gera um identificador único aleatório (um UUID versão 4). Usamos
# isso para dar um ID próprio a cada run raiz que criamos manualmente neste
# laboratório (cada fase do fluxo — iniciar, aprovar, etc. — é um run raiz
# separado, todos ligados pelo mesmo `thread_id`).
#
# `hashlib` é usado por `digest()` para calcular o hash SHA-256 de arquivos
# (ver `manifest()`). `platform` é usado por `manifest()` para registrar a
# versão do Python usada. `subprocess` é usado por `manifest()` para rodar
# comandos `git` e capturar a saída. `version` (de `importlib.metadata`) lê
# a versão instalada de um pacote Python (ex.: "langsmith").

# --- Constantes de caminho (ver explicação completa no lab 01) -----------
COURSE = Path(__file__).resolve().parents[1]
ROOT = COURSE.parent
ARTIFACTS = COURSE / "artefatos"

# `sys.path` é a lista de pastas onde o Python procura por módulos quando
# você escreve `import algo`. Inserir `ROOT / "src"` no INÍCIO dessa lista
# (posição 0) permite que este script encontre e importe o pacote `dcra`
# (o código de produção do projeto, que vive em `src/dcra/`), mesmo sem ele
# estar formalmente "instalado" no ambiente Python.
sys.path.insert(0, str(ROOT / "src"))


def parser(description: str) -> argparse.ArgumentParser:
    # Ver explicação linha a linha completa em 01_trace_python_full_explained.py.
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--send", action="store_true", help="Envia dados sintéticos ao seu LangSmith.")
    p.add_argument("--project", default=os.getenv("DCRA_LAB_PROJECT", "dcra-estudos"))
    return p


def configure(args: argparse.Namespace) -> None:
    # Liga/desliga o envio real ao LangSmith ANTES de qualquer run ser
    # criado, e garante que a API key exista quando `--send` é usado.
    # Explicação linha a linha completa: ver lab 01.
    enabled = "true" if args.send else "false"
    os.environ["LANGSMITH_TRACING"] = enabled
    os.environ["LANGCHAIN_TRACING_V2"] = enabled
    load_dotenv(ROOT / ".env", override=False)
    os.environ["LANGSMITH_PROJECT"] = args.project
    if args.send and not credential_present("LANGSMITH_API_KEY"):
        raise SystemExit("Preencha LANGSMITH_API_KEY em .env para usar --send. Veja 03-preparacao.md.")


def credential_present(name: str) -> bool:
    # Confirma que a variável de ambiente existe e não é um placeholder de
    # exemplo (ver explicação detalhada no lab 01).
    value = os.getenv(name, "").strip()
    return bool(value and "..." not in value and not value.startswith("<"))


def digest(path: Path) -> str:
    # `path.read_bytes()` lê o conteúdo do arquivo como bytes brutos (não
    # como texto — importante porque o hash precisa ser exatamente sobre os
    # bytes do arquivo, não sobre uma interpretação de texto que poderia
    # variar por codificação). `hashlib.sha256(...).hexdigest()` calcula a
    # "impressão digital" SHA-256 desses bytes e a devolve como uma string
    # hexadecimal (64 caracteres). Duas execuções do mesmo arquivo, byte a
    # byte idêntico, sempre produzem o mesmo hash — é assim que o
    # laboratório 05 identifica se o dataset local mudou.
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest() -> dict[str, Any]:
    """Registra o "estado do mundo" no momento da execução: commit do git,
    se há mudanças não commitadas, versão do Python, versões de pacotes
    chave e o hash de cada arquivo relevante. Isso é usado (no laboratório
    06, avaliação) para provar de forma auditável exatamente qual versão do
    código produziu um determinado resultado — útil em contextos
    acadêmicos/regulatórios onde reprodutibilidade importa.
    """
    # `subprocess.run([...], cwd=ROOT, text=True, capture_output=True, check=False)`
    # executa um comando externo (aqui, `git`) como se fosse digitado no
    # terminal, dentro da pasta `ROOT`. `text=True` faz a saída vir como
    # string (não bytes). `capture_output=True` guarda o texto que o
    # comando imprimiu (em vez de só mostrar na tela). `check=False` diz
    # "não lance uma exceção Python se o comando `git` falhar" — nós
    # tratamos isso manualmente abaixo, com o `.strip() or "indisponivel"`.
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    # `git status --porcelain` imprime uma linha por arquivo modificado/novo;
    # se a saída estiver vazia, a árvore de trabalho está "limpa" (sem
    # mudanças pendentes).
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, check=False
    )

    # `Path.glob("*.py")` lista arquivos que batem com o padrão (aqui,
    # "qualquer arquivo .py direto nesta pasta"); `.rglob("*.py")` faz o
    # mesmo mas de forma RECURSIVA (entra em subpastas também). `sorted(...)`
    # garante uma ordem estável e previsível entre execuções.
    paths = sorted((COURSE / "labs").glob("*.py"))
    # `+=` numa lista Python funciona como "estender a lista com estes itens"
    # (equivalente a `paths.extend(...)`), não como soma matemática.
    paths += sorted((COURSE / "evals").glob("*.py"))  # coleta, agregação e política do gate
    paths += sorted((ROOT / "src" / "dcra").rglob("*.py"))
    paths += sorted((COURSE / "dados").glob("*.json*"))
    # Colchetes `[...]` com um único caminho: cria uma lista de um item cada
    # e a concatena à lista `paths` (o arquivo de lock de dependências e o
    # arquivo de configuração do projeto).
    paths += [ROOT / "uv.lock", ROOT / "pyproject.toml"]

    # Este `return` monta e devolve um dicionário com várias informações.
    return {
        # `.stdout` é o texto que o comando imprimiu na saída padrão.
        # `.strip()` remove a quebra de linha final que o `git` sempre
        # adiciona. `or "indisponivel"` é um truque comum em Python: se o
        # lado esquerdo for "falsy" (aqui, string vazia — ex.: git falhou),
        # usa o valor do lado direito como alternativa.
        "git_sha": result.stdout.strip() or "indisponivel",
        # `bool(status.stdout.strip())`: True se sobrou algum texto depois
        # de remover espaços (ou seja, há mudanças não commitadas).
        "working_tree_dirty": bool(status.stdout.strip()),
        "python": platform.python_version(),
        # Dict comprehension: para cada `name` na lista, cria a chave
        # `name` com valor `version(name)` (a versão instalada desse
        # pacote Python). É equivalente a um `for` que vai preenchendo um
        # dicionário, mas em uma linha só.
        "packages": {name: version(name) for name in ["langsmith", "langchain", "langgraph"]},
        # Outra dict comprehension: para cada `p` em `paths` que realmente
        # existe no disco (`if p.exists()`), a chave é o caminho relativo
        # (como texto) e o valor é o hash SHA-256 desse arquivo.
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
    """Lê o arquivo `dados/casos.jsonl`: um formato onde cada LINHA do
    arquivo é um objeto JSON independente (diferente de um `.json` comum,
    que é um único objeto/lista grande). É um formato muito usado para
    conjuntos de dados, porque permite processar arquivo linha a linha sem
    carregar tudo na memória de uma vez (aqui carregamos tudo mesmo assim,
    já que o arquivo é pequeno, mas o formato continua conveniente).
    """
    path = COURSE / "dados" / "casos.jsonl"
    # `path.read_text()` lê o arquivo inteiro como uma string.
    # `.splitlines()` quebra essa string em uma lista de linhas.
    # A list comprehension abaixo lê cada `line`, ignora linhas em branco
    # (`if line.strip()` — string vazia é "falsy"), e converte cada linha
    # não vazia de JSON-texto para um dicionário Python com `json.loads`.
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@contextmanager
def session(args: argparse.Namespace, *, lab: str) -> Iterator[Any]:
    # Gerenciador de contexto que abre a sessão de tracing do LangSmith.
    # Explicação linha a linha completa: ver lab 01.
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

    (Explicação linha a linha completa desta função: ver lab 01. A única
    diferença de uso aqui é que este laboratório chama `show_trace` várias
    vezes — uma para cada "fase" do fluxo — porque cada fase é um run raiz
    diferente, mesmo que todas compartilhem o mesmo `thread_id`.)
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
    """Validação de segurança/custo: só permite chamar um modelo de
    linguagem REAL (que gera cobrança no provedor, ex.: OpenAI ou
    Anthropic) se o usuário passou explicitamente `--real` E configurou
    corretamente as variáveis de ambiente necessárias. Isso evita que
    alguém rode o laboratório sem querer e receba uma cobrança inesperada.
    """
    # `args.real` só existe porque, mais abaixo em `main()`, adicionamos
    # `p.add_argument("--real", ...)` ao parser deste laboratório
    # específico (o parser genérico do topo não conhece essa opção).
    if not args.real:
        raise SystemExit("Este laboratório exige --real para chamar o provedor de modelo.")
    if not os.getenv("LLM_MODEL"):
        raise SystemExit("Defina LLM_MODEL com um modelo disponível na sua conta.")
    provider = os.getenv("LLM_PROVIDER", "openai")
    # `{"openai": "...", "anthropic": "..."}.get(provider)` procura a chave
    # `provider` no dicionário; se não existir, devolve `None` em vez de
    # lançar erro (diferente de usar `dicionario[provider]`, que quebraria).
    key = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(provider)
    if key is None or not credential_present(key):
        raise SystemExit("Configure LLM_PROVIDER e a chave correspondente no .env do projeto.")


def real_model():
    # Import local: só carrega o código de configuração/fábrica de modelos
    # do projeto (`dcra.config`, `dcra.llm.factory`) quando esta função é
    # de fato chamada (ou seja, quando `--real` foi usado).
    from dcra.config import Settings
    from dcra.llm.factory import build_chat_model

    # Modelo e integração que o projeto já usa; sem atualizar dependências.
    return build_chat_model(Settings.from_env())


# ============================================================================
# A PARTIR DAQUI começa a lógica específica deste laboratório (rodar o grafo
# real do DCRA).
# ============================================================================

# Dicionário que mapeia um "apelido" de cenário (usado no `--case`) para o
# texto bruto de uma mudança de schema hipotética. Cada linha descreve uma
# operação de banco de dados que o DCRA vai classificar por nível de risco.
SCENARIOS = {
    "low": "add index on orders(customer_id)",
    "medium": "drop column orders.customer_legacy_id",
    "high": "drop column orders.id",
    "unknown": "drop column orders.legacy_region",
    "gap": "drop column orders.customer_legacy_id",
}


def main():
    p = parser(__doc__)
    # `choices=SCENARIOS` faz o argparse aceitar como valor válido de
    # `--case` apenas uma das CHAVES do dicionário `SCENARIOS` (quando você
    # passa um dicionário para `choices`, o argparse itera sobre suas
    # chaves automaticamente). Se o usuário digitar um valor fora dessa
    # lista, o argparse já mostra um erro amigável sozinho.
    p.add_argument("--case", choices=SCENARIOS, default="medium")
    # Esta opção controla que "decisão humana" simular durante a pausa de
    # revisão do grafo (explicado mais abaixo).
    p.add_argument("--review", choices=["none", "approve", "reject", "return", "return-evidence"],
                   default="none")
    p.add_argument("--real", action="store_true", help="Usa LLM real e gera cobrança no provedor.")
    args = p.parse_args()

    with session(args, lab="02-dcra") as client:
        # Imports locais: carregam o código de produção do projeto DCRA
        # (a lógica real do grafo, não uma simulação) e utilitários do
        # LangSmith específicos desta seção.
        from _dcra import make_deps, review, summarize
        from langsmith import tracing_context

        from dcra.domain.models import ChangeRequest
        from dcra.graph.build import build_graph, pending_interrupt, run

        if args.real:
            require_real(args)

        # `build_graph(...)` monta o grafo de execução do DCRA (uma máquina
        # de estados definida com LangGraph) já configurado com as
        # dependências fixture (catálogo de banco simulado) ou reais.
        # `["usage"] if args.case == "gap" else []` decide, com um
        # operador ternário dentro de uma lista, se o cenário "gap" precisa
        # de uma dependência extra chamada "usage" (simulando ausência de
        # dados de uso real da coluna) — isso é específico da lógica de
        # negócio do DCRA, não do LangSmith.
        graph = build_graph(make_deps(["usage"] if args.case == "gap" else [], real=args.real))

        # Cria um objeto de domínio representando a solicitação de mudança:
        # o texto bruto do cenário escolhido, mais quem "submeteu" (aqui,
        # um usuário sintético fixo).
        cr = ChangeRequest(raw_text=SCENARIOS[args.case], submitted_by="aluno-sintetico")

        # Lista vazia que vai acumular um resumo de cada "fase" da execução
        # (início, e depois cada retomada após revisão).
        phases = []

        # Metadados compartilhados por TODOS os runs raiz deste laboratório.
        # `cr.id` funciona como o `thread_id`: o identificador que amarra
        # todas as fases de UM MESMO caso, mesmo sendo runs raiz diferentes
        # no LangSmith — assim, na UI, dá para filtrar por thread_id e ver
        # a história completa de um caso, do início até a decisão final.
        metadata = {"thread_id": cr.id, "scenario": args.case,
                    "model_mode": "real" if args.real else "fixture"}

        # `tracing_context(metadata=metadata)` (sem outros argumentos, além
        # do já aberto por `session(...)` acima) MESCLA este `metadata`
        # extra com o que já estava ativo, para que todo run criado dentro
        # deste bloco carregue também `thread_id`, `scenario` e `model_mode`.
        with tracing_context(metadata=metadata):
            # `uuid4()` gera um ID novo e aleatório; `str(...)` o converte
            # em texto. Usamos esse ID como o `run_id` do PRÓXIMO run raiz
            # que vamos criar manualmente (em vez de deixar o LangSmith
            # gerar um automaticamente) — assim sabemos de antemão qual
            # será o ID, útil para buscá-lo logo em seguida com `show_trace`.
            root_id = str(uuid4())

            # `graph.with_config(...)` devolve uma NOVA versão do grafo com
            # configurações extras aplicadas (não modifica `graph` original
            # — é um padrão comum em LangGraph/LangChain chamado "runnable
            # config"). Aqui definimos:
            #   - run_name: nome deste run raiz na UI do LangSmith
            #   - run_id: o ID que acabamos de gerar acima
            #   - metadata: informação extra específica desta chamada
            configured = graph.with_config(run_name="dcra-iniciar", run_id=root_id, metadata=metadata)

            # `run(configured, cr)` (função importada de `dcra.graph.build`,
            # NÃO tem relação com o `run` do LangSmith usado no lab 01/03)
            # executa o grafo do zero para esta ChangeRequest. O grafo pode
            # PARAR NO MEIO se atingir um ponto de "interrupção" (uma
            # pausa que espera uma decisão humana — por exemplo, quando o
            # risco calculado exige revisão manual antes de prosseguir).
            # `state` guarda o estado do grafo no momento em que ele parou
            # (ou terminou, se não houve pausa).
            state = run(configured, cr)

            # `summarize(state, cr.id)` (função auxiliar do laboratório,
            # definida em `_dcra.py`) extrai do estado bruto do grafo um
            # dicionário resumido e legível (risco, se está pausado
            # aguardando revisão, etc.). O operador `|` entre dois
            # dicionários (disponível desde o Python 3.9) cria um NOVO
            # dicionário mesclando os dois — aqui, o resumo mais o
            # `run_id` desta fase. `phases.append(...)` adiciona esse
            # dicionário ao final da lista `phases`.
            phases.append(summarize(state, cr.id) | {"run_id": root_id})

            if client:
                show_trace(client, args.project, root_id)

            # Dicionário que traduz o valor de `--review` em uma LISTA de
            # decisões a simular, em ordem. Por exemplo, `"return-evidence"`
            # significa "primeiro devolva o caso pedindo mais evidência,
            # depois aprove" — duas retomadas em sequência.
            actions = {"none": [], "approve": ["APPROVE"], "reject": ["REJECT"],
                       "return": ["RETURN", "APPROVE"], "return-evidence": ["RETURN", "APPROVE"]}

            # `for decision in actions[args.review]:` percorre essa lista de
            # decisões, uma de cada vez.
            for decision in actions[args.review]:
                # `pending_interrupt(state)` verifica se o grafo está, neste
                # momento, parado esperando uma decisão humana. Se não
                # estiver (`is None`), não há nada para revisar — isso pode
                # acontecer se o caso for de risco baixo (não exige revisão)
                # ou se algo deu errado antes. `break` interrompe o `for`.
                if pending_interrupt(state) is None:
                    print("Não há pausa para revisar: confira se o caso é LOW ou ocorreu um erro.")
                    break

                # Cada retomada do grafo também vira um NOVO run raiz
                # próprio (novo `root_id`), mas ainda ligado ao mesmo
                # `thread_id` (via `metadata`) — assim o LangSmith mostra a
                # jornada completa do caso como uma sequência de runs
                # relacionados, não como um único run gigante.
                root_id = str(uuid4())

                # `decision.lower()` transforma o texto (ex.: "APPROVE") em
                # minúsculas ("approve"), só para compor um nome de run mais
                # legível na UI: "dcra-retomar-approve".
                configured = graph.with_config(run_name=f"dcra-retomar-{decision.lower()}",
                                               run_id=root_id, metadata=metadata)

                # `review(...)` (de `_dcra.py`) retoma o grafo a partir de
                # onde ele pausou, aplicando a `decision` simulada.
                # `evidence_missing=...` é um parâmetro específico do
                # cenário "return-evidence": só é `True` quando estamos na
                # decisão "RETURN" desse cenário específico (comparação com
                # `and`: as duas condições precisam ser verdadeiras).
                state = review(configured, cr.id, decision,
                               evidence_missing=args.review == "return-evidence" and decision == "RETURN")
                phases.append(summarize(state, cr.id) | {"run_id": root_id})
                if client:
                    show_trace(client, args.project, root_id)

        # Fora do `with tracing_context(...)`: já terminamos todas as fases.
        print(f"thread_id: {cr.id}")

        # `enumerate(phases, 1)` percorre a lista `phases` devolvendo pares
        # (posição, item), começando a contagem em 1 (em vez do padrão 0) —
        # só para a numeração impressa ficar amigável ("Fase 1", "Fase 2"...).
        for n, phase in enumerate(phases, 1):
            # f-string de várias linhas (duas strings literais adjacentes
            # são automaticamente concatenadas pelo Python — não precisa de
            # operador `+` entre elas). `phase['risk']` acessa a chave
            # `"risk"` do dicionário `phase`.
            print(f"Fase {n}: risco={phase['risk']} pausa={phase['awaiting_review']} "
                  f"resultado={phase['outcome']} versões={phase['recommendation_versions']}")

        # `"\n".join(lista)` junta uma lista de strings em uma única string,
        # colocando uma quebra de linha entre cada item — imprime o log de
        # passos (step_log) da ÚLTIMA fase (`phases[-1]`, índice negativo
        # significa "contar a partir do fim da lista").
        print("\n".join(phases[-1]["step_log"]))

        # Salva um resumo de toda a execução em um arquivo JSON, cujo nome
        # inclui o cenário e o tipo de revisão usados (ex.: "02-medium-none.json").
        write_json(f"02-{args.case}-{args.review}.json", {"mode": metadata["model_mode"], "phases": phases})


if __name__ == "__main__":
    main()
