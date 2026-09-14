"""Versão comentada, linha a linha, do laboratório 01 (trace de Python puro).

Este arquivo NÃO é um laboratório novo: é `01_trace_python_full.py` com uma
explicação didática ao lado de (quase) cada linha. O objetivo é ensinar duas
coisas ao mesmo tempo:

1. Python "do dia a dia" que aparece neste script: imports, funções,
   decoradores, gerenciadores de contexto (`with`), dicionários, f-strings,
   tratamento de exceções etc.
2. Os conceitos de LangSmith usados aqui: o que é um "run", o que é um
   "trace", a diferença entre `trace()` (gerenciador de contexto) e
   `@traceable` (decorador), o que é o `Client`, e o que significa "enviar"
   ou não um trace.

Contexto do exercício: simulamos um "pedido de restaurante" (sem nenhum
modelo de IA envolvido) só para observar, na prática, como o LangSmith
organiza um run raiz e dois runs filhos dentro dele.

Como ler este arquivo: leia de cima para baixo, como um tutorial. Os blocos
de comentário grandes (com `# ---`) introduzem uma seção; os comentários
curtos ao lado do código (`# ...`) explicam a linha específica.
"""

# `from __future__ import annotations` é um "recurso do futuro" do Python.
# Ele faz com que as anotações de tipo (as partes como `-> Path` ou
# `arg: str`) sejam tratadas como texto (strings) em vez de serem avaliadas
# imediatamente. Na prática isso permite escrever tipos como `datetime | None`
# mesmo em versões do Python onde essa sintaxe só passou a existir depois,
# e evita alguns erros de "referência circular" entre tipos. Você pode não
# perceber diferença nenhuma rodando o script: o efeito é só para o
# verificador de tipos (ex.: mypy/pyright) e para legibilidade.
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

# --- Bloco de imports: trazendo "caixas de ferramentas" prontas -----------
# Em Python, `import X` carrega um módulo inteiro (uma "biblioteca"), e você
# acessa suas funções como `X.funcao()`. Todos os módulos de `argparse` até
# `typing` fazem parte da biblioteca padrão do Python (não precisam ser
# instalados via pip):
#   - argparse: cria a interface de linha de comando (as opções --send, --project etc.)
#   - asyncio: permite rodar código "assíncrono" (que espera respostas de rede) dentro de um script comum
#   - json: converte dados Python (dict, list, str, int...) para/de texto JSON
#   - os: acessa variáveis de ambiente do sistema operacional (os.environ, os.getenv)
#   - time: fornece `time.sleep` (pausar) e `time.perf_counter` (cronômetro de precisão)
#
# `from modulo import algo` importa só uma peça específica do módulo, em vez
# do módulo inteiro. Assim usamos `Iterator` diretamente, sem escrever
# `collections.abc.Iterator` toda vez:
#   - Iterator: tipo usado para anotar "algo que pode ser percorrido com for"
#   - contextmanager: decorador que transforma uma função geradora em um gerenciador de contexto (`with ...:`)
#   - datetime: tipo de data/hora, usado para carimbar quando um run começou
#   - Path: representa caminhos de arquivos/pastas de forma orientada a objetos (em vez de strings puras)
#   - Any: tipo "coringa", significa "qualquer tipo de valor", usado quando o tipo exato não importa aqui
#
# Estas duas últimas vêm de bibliotecas externas (instaladas via pip/uv, não
# fazem parte do Python "de fábrica"):
#   - load_dotenv: lê um arquivo `.env` e transforma cada linha KEY=VALOR em variável de ambiente
#   - trace, traceable: as duas ferramentas centrais do LangSmith usadas neste lab (explicadas mais abaixo)

# --- Constantes de caminho ---------------------------------------------
# Em Python, nomes escritos em MAIÚSCULAS por convenção são "constantes":
# valores que não devem mudar durante a execução do programa.

# `__file__` é uma variável mágica que o Python preenche automaticamente com
# o caminho deste próprio arquivo `.py`. `Path(__file__)` transforma esse
# texto em um objeto `Path`, que sabe fazer contas de caminho.
# `.resolve()` troca o caminho por sua versão absoluta (sem "..", sem atalhos).
# `.parents[1]` sobe dois níveis de pasta: `.parents[0]` seria a pasta que
# contém este arquivo (labs/), `.parents[1]` é a pasta acima dela
# (ESTUDOS_LANGSMITH/). Ou seja: COURSE aponta para a raiz do curso.
COURSE = Path(__file__).resolve().parents[1]

# `.parent` (sem índice) sobe mais um nível: a raiz do repositório do projeto.
ROOT = COURSE.parent

# O operador `/` entre objetos `Path` NÃO é divisão matemática aqui: a
# biblioteca `pathlib` sobrecarrega (redefine) esse operador para significar
# "junte este pedaço de caminho". Então isso monta a pasta
# ESTUDOS_LANGSMITH/artefatos, onde os arquivos JSON gerados pelos labs são salvos.
ARTIFACTS = COURSE / "artefatos"


# --- Função: construir o parser de linha de comando ------------------------
# `def nome(parametros) -> TipoDeRetorno:` declara uma função. A seta `->`
# é só documentação de tipo (não é obrigatória para o código rodar).
def parser(description: str) -> argparse.ArgumentParser:
    # `argparse.ArgumentParser` é a classe padrão do Python para interpretar
    # argumentos digitados no terminal (tipo `python script.py --send`).
    # Criar uma instância dela é como "abrir um formulário" que vamos
    # preencher com `.add_argument(...)` abaixo.
    p = argparse.ArgumentParser(description=description)

    # `.add_argument("--send", action="store_true", ...)` cria uma opção
    # booleana: se o usuário digitar `--send` no terminal, o valor fica
    # `True`; se não digitar, fica `False` por padrão. `help=` é o texto
    # mostrado quando alguém roda `python script.py --help`.
    p.add_argument("--send", action="store_true", help="Envia dados sintéticos ao seu LangSmith.")

    # Esta opção recebe um valor de texto (ex.: `--project meu-projeto`).
    # `default=os.getenv("DCRA_LAB_PROJECT", "dcra-estudos")` significa:
    # "se a variável de ambiente DCRA_LAB_PROJECT existir, use-a como
    # padrão; senão, use a string 'dcra-estudos'". `os.getenv(nome, padrao)`
    # nunca lança erro mesmo se a variável não existir — é a forma segura
    # de ler variáveis de ambiente opcionais.
    p.add_argument("--project", default=os.getenv("DCRA_LAB_PROJECT", "dcra-estudos"))

    # A função devolve o objeto `p` já configurado, pronto para que quem
    # chamou rode `.parse_args()` nele (isso é feito lá no `main()`).
    return p


# --- Função: preparar as variáveis de ambiente antes de qualquer chamada ---
# `args: argparse.Namespace` é o objeto devolvido por `parser(...).parse_args()`:
# um "pacote" com um atributo para cada `--opcao` que definimos acima
# (ex.: `args.send`, `args.project`).
def configure(args: argparse.Namespace) -> None:
    # `-> None` indica que esta função não devolve nenhum valor útil: ela só
    # produz "efeitos colaterais" (aqui, mexer em variáveis de ambiente).

    # Operador ternário do Python: `A if condicao else B` avalia para A
    # quando a condição é verdadeira, e para B caso contrário. Aqui,
    # convertemos o booleano `args.send` (True/False) para o texto
    # "true"/"false", porque variáveis de ambiente só guardam texto.
    enabled = "true" if args.send else "false"

    # `os.environ` é um dicionário especial que representa as variáveis de
    # ambiente do processo atual. Atribuir a uma chave dele
    # (`os.environ["X"] = valor`) define/sobrescreve essa variável para todo
    # o resto da execução do script (e para bibliotecas que a leiam depois).
    #
    # LANGSMITH_TRACING (e seu nome antigo, LANGCHAIN_TRACING_V2) é a
    # variável de ambiente que o SDK do LangSmith verifica para decidir se
    # deve de fato enviar os runs para o servidor. Setá-la aqui ANTES de
    # qualquer `trace(...)`/`@traceable` ser executado é o que liga ou
    # desliga o envio real de dados.
    os.environ["LANGSMITH_TRACING"] = enabled
    os.environ["LANGCHAIN_TRACING_V2"] = enabled

    # `load_dotenv(caminho, override=False)` procura um arquivo `.env` na
    # raiz do projeto e copia cada linha `CHAVE=valor` dele para
    # `os.environ`, mas só para chaves que AINDA NÃO existem no ambiente
    # (`override=False`). É assim que a chave de API do LangSmith
    # (LANGSMITH_API_KEY) chega até o processo sem estar escrita no código.
    load_dotenv(ROOT / ".env", override=False)

    # Define explicitamente em qual "projeto" (workspace/dashboard) do
    # LangSmith os runs devem aparecer.
    os.environ["LANGSMITH_PROJECT"] = args.project

    # Checagem de segurança: se o usuário pediu `--send` mas não configurou
    # a chave de API, é melhor falhar cedo com uma mensagem clara do que
    # deixar o LangSmith rejeitar silenciosamente depois.
    # `raise SystemExit("mensagem")` interrompe o programa imediatamente e
    # mostra essa mensagem no terminal (é o mecanismo usado por scripts de
    # linha de comando para "sair com erro e explicação").
    if args.send and not credential_present("LANGSMITH_API_KEY"):
        raise SystemExit("Preencha LANGSMITH_API_KEY em .env para usar --send. Veja 03-preparacao.md.")


# --- Função auxiliar: a variável de ambiente está de fato preenchida? ------
def credential_present(name: str) -> bool:
    # `os.getenv(name, "")` lê a variável de ambiente `name`; se ela não
    # existir, devolve string vazia em vez de `None` (assim os métodos de
    # string abaixo, como `.strip()`, não quebram).
    # `.strip()` remove espaços em branco do início/fim (ex.: se alguém
    # colou a chave com um espaço extra sem perceber).
    value = os.getenv(name, "").strip()

    # `bool(...)` converte o resultado final em True/False. A expressão
    # inteira só é True quando TODAS as três condições, unidas por `and`,
    # são verdadeiras:
    #   1. `value` não é uma string vazia (strings vazias são "falsy" em Python)
    #   2. `"..." not in value` — o placeholder de exemplo no `.env.example`
    #      costuma usar reticências (ex.: "lsv2_pt_...seuvalor..."); se
    #      ainda tiver "...", é sinal de que ninguém trocou pelo valor real.
    #   3. `not value.startswith("<")` — outro padrão comum de placeholder
    #      é algo como "<cole-sua-chave-aqui>"; se começar com "<", também
    #      não é uma chave real.
    return bool(value and "..." not in value and not value.startswith("<"))


# --- Função: salvar qualquer valor Python como arquivo JSON legível --------
def write_json(name: str, value: Any) -> Path:
    # `Path.mkdir(exist_ok=True)` cria a pasta `artefatos/` se ela ainda não
    # existir. `exist_ok=True` evita que o programa quebre com erro caso a
    # pasta já exista (comportamento padrão do `mkdir` seria lançar erro).
    ARTIFACTS.mkdir(exist_ok=True)

    # Monta o caminho completo do arquivo de saída (ex.: .../artefatos/01-trace.json).
    path = ARTIFACTS / name

    # `json.dumps(valor, ...)` transforma uma estrutura Python (dict, list,
    # str, int, bool, None) em uma STRING de texto no formato JSON.
    #   - `indent=2`: identa o JSON com 2 espaços, deixando-o legível para humanos.
    #   - `ensure_ascii=False`: permite salvar acentos (ç, ã, á...) como
    #     caracteres normais, em vez de escapá-los como ç etc.
    #   - `default=str`: quando o JSON encontra um tipo que ele não sabe
    #     serializar nativamente (como um objeto `datetime` ou `UUID`), em
    #     vez de lançar erro, ele chama `str(...)` nesse valor e usa o
    #     resultado. É assim que datas e IDs de run viram texto no arquivo.
    # `+ "\n"` só adiciona uma quebra de linha final, por estética/POSIX.
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")

    # `path.relative_to(ROOT)` reescreve o caminho absoluto como relativo à
    # raiz do projeto, só para a mensagem impressa ficar mais curta e legível.
    print(f"Arquivo: {path.relative_to(ROOT)}")

    # Devolve o `Path` do arquivo criado, caso quem chamou queira usá-lo.
    return path


# --- Gerenciador de contexto: abre e fecha a "sessão" de tracing ----------
# `@contextmanager` é um decorador (explicado com mais detalhe logo abaixo,
# nos usos de `@traceable`). Ele pega uma função "geradora" (que usa `yield`
# em vez de `return`) e a transforma em algo que pode ser usado com a
# sintaxe `with session(...) as client:`. Tudo antes do `yield` roda quando
# o `with` COMEÇA; tudo depois do `yield` (inclusive o `finally`) roda
# quando o bloco `with` TERMINA — mesmo que tenha ocorrido um erro dentro dele.
@contextmanager
def session(args: argparse.Namespace, *, lab: str) -> Iterator[Any]:
    # O `*` na assinatura `def session(args, *, lab: str)` obriga quem chama
    # a escrever `lab="algo"` explicitamente (não pode passar por posição,
    # tipo `session(args, "01-python")`). Isso deixa o código de quem chama
    # mais legível, forçando o nome do parâmetro a aparecer.

    # Este `import` está DENTRO da função (um "import local"), não no topo
    # do arquivo. Isso é comum quando o import é "pesado" (carrega bastante
    # coisa) e só é necessário quando a função de fato roda — evita atrasar
    # a inicialização do script inteiro.
    from langsmith import Client, tracing_context

    # Garante que LANGSMITH_TRACING/LANGSMITH_PROJECT estejam configurados
    # antes de criar o Client (repete a função explicada acima).
    configure(args)

    # `Client` é a classe do SDK do LangSmith que sabe conversar com a API
    # (criar runs, ler projetos, anexar feedback etc.). Só criamos essa
    # conexão de fato se `--send` foi passado; caso contrário, `client`
    # fica `None` e o restante do script sabe que está em "modo local"
    # (sem nenhuma chamada de rede).
    client = Client() if args.send else None

    # `try/finally` garante que o bloco dentro de `finally` rode SEMPRE,
    # mesmo que algo dê erro dentro do `try`. Aqui isso é importante para
    # garantir que os dados pendentes sejam enviados ao LangSmith mesmo se
    # o código do usuário (dentro do `with session(...) as client:`) lançar
    # uma exceção.
    try:
        # `tracing_context(...)` é outro gerenciador de contexto do
        # LangSmith. Enquanto estivermos "dentro" dele, todo `trace(...)`
        # ou função `@traceable` chamada herda automaticamente estas
        # configurações padrão, sem precisar repeti-las toda vez:
        #   - enabled: liga/desliga o envio (mesmo valor de --send)
        #   - client: qual conexão usar para enviar
        #   - project_name: em qual projeto do LangSmith os runs aparecem
        #   - tags: etiquetas aplicadas a todos os runs criados aqui dentro
        #   - metadata: informações extras (visíveis na UI do LangSmith)
        #     anexadas a cada run
        with tracing_context(
            enabled=args.send,
            client=client,
            project_name=args.project,
            tags=["estudo", lab],
            metadata={"environment": "lab", "lab": lab, "synthetic": True},
        ):
            # `yield client` é o coração de um gerenciador de contexto
            # feito com `@contextmanager`: ele "pausa" esta função aqui,
            # devolve `client` para quem escreveu `with session(...) as client:`,
            # e deixa o código de dentro do `with` do chamador rodar. Quando
            # aquele bloco termina (ou dá erro), a execução volta para CÁ,
            # logo depois do `yield`.
            yield client
    finally:
        # Depois que o bloco `with` do chamador terminar (com ou sem erro),
        # se um `client` de verdade foi criado, mandamos ele "descarregar"
        # (`flush`) qualquer run que ainda esteja em fila de envio, esperando
        # até 10 segundos por isso. Sem isso, alguns runs poderiam ficar
        # pendentes no buffer interno e nunca chegar ao servidor antes do
        # script terminar.
        if client is not None:
            client.flush(timeout=10)


# --- Função: buscar e imprimir a URL pública do trace no LangSmith --------
def show_trace(client: Any, project: str, run_id: str, *, start_time: datetime | None = None) -> None:
    """URL autenticada do run, pedida ao endpoint v2 do LangSmith; nunca um link montado à mão.

    No SmithDB um run é endereçado por (projeto, trace_id, run_id); `start_time` é opcional e
    acelera a busca. Aqui o run é sempre a raiz, logo trace_id == run_id. Os métodos v2 do SDK
    (`client.runs.*`) são assíncronos: `asyncio.run` executa a corrotina neste script síncrono.

    (Esta docstring — o texto entre aspas triplas logo abaixo da assinatura
    da função — já existia no laboratório original; aqui ela explica, em
    poucas palavras, POR QUE a função existe. Comentários com `#` abaixo
    explicam COMO, linha a linha.)
    """
    # Estas exceções específicas do LangSmith são importadas aqui dentro
    # porque só interessam a esta função: representam "não encontrei esse
    # run/projeto ainda" — algo que pode acontecer nos primeiros instantes
    # depois de criar um run, antes de ele ficar disponível para consulta.
    from langsmith import NotFoundError
    from langsmith.utils import LangSmithNotFoundError

    # Antes de perguntar pela URL, garantimos que o run já foi de fato
    # enviado ao servidor (não fique só no buffer local).
    client.flush(timeout=10)
    print(f"run_id: {run_id}")

    # `for attempt in range(3):` repete o bloco 3 vezes, com `attempt`
    # assumindo os valores 0, 1 e 2. Chamamos isso de "retry com tentativas
    # limitadas": tentamos até 3 vezes, porque o servidor do LangSmith pode
    # levar um instante para indexar um run recém-criado.
    for attempt in range(3):  # o projeto e o run podem levar instantes para ficar consultáveis
        try:
            # `client.read_project(project_name=project)` pergunta ao
            # LangSmith qual é o ID interno (um UUID) do projeto cujo nome
            # é `project`. Precisamos desse ID (não do nome) para montar a
            # URL corretamente. `str(...)` converte o UUID para texto.
            project_id = str(client.read_project(project_name=project).id)

            # `client.runs.get_url(...)` é um método "assíncrono" (definido
            # com `async def` dentro do SDK): ele não devolve o resultado
            # na hora, devolve uma "promessa" de resultado (uma corrotina)
            # que precisa ser "executada" de verdade. Como o resto do nosso
            # script é síncrono (não usa `async`/`await`), usamos
            # `asyncio.run(...)` para rodar essa corrotina até o fim e
            # pegar o valor final — é a ponte entre o mundo síncrono
            # (nosso script) e o mundo assíncrono (o SDK v2).
            response = asyncio.run(client.runs.get_url(
                run_id, project_id=project_id, trace_id=run_id, start_time=start_time))

            # Se a resposta já trouxer uma URL pronta, imprimimos e saímos
            # da função (`return` sem valor, já que `-> None`).
            if response.url:
                print(f"Trace: {response.url}")
                return

            # Caso contrário, esperamos um pouco antes de tentar de novo.
            # `0.5 * (attempt + 1)` cresce a cada tentativa (0.5s, 1.0s,
            # 1.5s) — um "backoff" simples para dar mais tempo ao servidor.
            time.sleep(0.5 * (attempt + 1))
        except (LangSmithNotFoundError, NotFoundError):
            # "Ainda não encontrado" é esperado logo após criar o run:
            # tratamos como sinal para tentar de novo, não como erro fatal.
            time.sleep(0.5 * (attempt + 1))
        except Exception as exc:
            # `Exception` é a classe "avó" de quase todo erro em Python.
            # Capturá-la aqui é uma rede de segurança para qualquer outro
            # problema inesperado (ex.: falha de rede): em vez de derrubar
            # o script inteiro, avisamos o usuário e desistimos de tentar
            # mostrar a URL — o resto do laboratório continua funcionando.
            # `type(exc).__name__` pega só o NOME da classe do erro (ex.:
            # "ConnectionError"), sem o texto completo, para uma mensagem curta.
            print(f"URL ainda indisponível ({type(exc).__name__}).")
            break  # sai do laço `for` imediatamente, sem mais tentativas

    # Se as 3 tentativas esgotarem sem sucesso (ou se demos `break`), pelo
    # menos deixamos instruções manuais de onde procurar o trace.
    print(f"Abra https://smith.langchain.com → Tracing → {project}; procure pelo run_id acima.")


# ============================================================================
# A PARTIR DAQUI começa a lógica específica DESTE laboratório (o "pedido de
# restaurante"). Tudo acima era infraestrutura reutilizável (equivalente ao
# antigo `_common.py`).
# ============================================================================

# --- @traceable: o decorador que transforma uma função comum em um "run" --
#
# O que é um DECORADOR em Python? É uma função que recebe outra função e
# devolve uma versão "envolvida" dela. A sintaxe `@algo` colocada acima de
# `def minha_funcao(...):` é um atalho para escrever
# `minha_funcao = algo(minha_funcao)`. Ou seja: `@traceable(...)` substitui
# a função `menu` por uma nova versão que, por baixo dos panos, faz tudo que
# `menu` fazia, MAS também: cria um "run" no LangSmith, cronometra quanto
# tempo a função levou, guarda os argumentos recebidos (`inputs`) e o valor
# devolvido (`outputs`), e registra se houve erro.
#
# `run_type="tool"` classifica este run na interface do LangSmith como uma
# chamada de "ferramenta" (não um modelo de linguagem, não uma cadeia — só
# uma função utilitária). `name="consultar_cardapio"` é o nome que aparece
# na árvore de runs do LangSmith (pode ser diferente do nome da função
# Python).
@traceable(run_type="tool", name="consultar_cardapio")
def menu(item: str) -> dict:
    # Corpo simples: devolve um dicionário fixo simulando uma consulta a um
    # cardápio. Como a função está decorada com `@traceable`, o LangSmith
    # (quando o tracing está ligado) grava automaticamente que esta função
    # foi chamada com `{"item": item}` e devolveu este dicionário — sem que
    # precisemos escrever nenhum código extra aqui dentro.
    return {"item": item, "preco_reais": 18, "disponivel": True}


# Outro exemplo de `@traceable`, desta vez sem `run_type` explícito (o
# padrão é `"chain"`, ou seja, "uma etapa de processamento genérica").
@traceable(name="calcular_total")
def total(price: int, quantity: int) -> int:
    # Multiplicação simples. De novo, o interessante não é a lógica (é só
    # uma conta), e sim que o LangSmith vai registrar este cálculo como um
    # run filho, com seus próprios inputs/outputs e tempo de execução.
    return price * quantity


# Esta função NÃO tem `@traceable`: ela é só "código Python comum" que
# organiza a chamada das duas funções rastreadas acima. Isso é proposital,
# para mostrar que você escolhe exatamente quais funções quer que apareçam
# como runs — nem tudo precisa ser decorado.
def order(inputs: dict) -> dict:
    # Chama a função rastreada `menu`, passando o item pedido.
    item = menu(inputs["item"])

    # Monta o dicionário de resultado final. A chave `"total_reais"` chama
    # a função rastreada `total`, passando o preço obtido do cardápio e a
    # quantidade pedida.
    return {"total_reais": total(item["preco_reais"], inputs["quantidade"]), "moeda": "BRL"}


def main():
    # `parser(__doc__)` usa a docstring deste MÓDULO (o texto entre aspas
    # triplas lá no topo do arquivo, acessível pela variável mágica
    # `__doc__`) como descrição do comando de linha de comando (aparece em
    # `--help`). `.parse_args()` de fato lê `sys.argv` (os argumentos
    # digitados no terminal) e devolve o objeto `Namespace` com os valores.
    args = parser(__doc__).parse_args()

    # Dados de entrada fixos (sintéticos) para este exercício: um pedido de
    # "risoto de dados", quantidade 2.
    inputs = {"item": "risoto-de-dados", "quantidade": 2}

    # Abre a sessão de tracing (explicada acima). `client` será um objeto
    # `Client` de verdade se `--send` foi passado, ou `None` caso contrário.
    with session(args, lab="01-python") as client:
        # `trace(...)` é a OUTRA forma (além de `@traceable`) de criar um
        # run no LangSmith: em vez de decorar uma função inteira, você
        # abre manualmente um bloco `with trace(...) as run:` ao redor do
        # trecho de código que quer rastrear. Isso cria o RUN RAIZ desta
        # execução — o "nó" no topo da árvore de runs. Qualquer função
        # `@traceable` chamada DENTRO deste bloco (como `order`, que chama
        # `menu` e `total`) vira automaticamente um run FILHO deste run raiz,
        # formando uma árvore/trace completo.
        #
        #   - "pedido-restaurante": nome do run raiz na UI do LangSmith.
        #   - inputs=inputs: os dados de entrada gravados para este run.
        #   - metadata={...}: informação extra anexada ao run (aqui, o
        #     cenário do teste), útil para filtrar/buscar depois na UI.
        #   - `as run`: o objeto `run` devolvido representa este run raiz —
        #     é através dele que conseguimos, por exemplo, ler `run.id` e
        #     `run.start_time`, ou chamar `run.end(...)` para fechá-lo.
        with trace("pedido-restaurante", inputs=inputs, metadata={"scenario": "pedido-valido"}) as run:
            # Executa a lógica de negócio de verdade. Isso dispara, por
            # baixo dos panos, as chamadas a `menu(...)` e `total(...)`,
            # cada uma virando um run filho (se o tracing estiver ativo).
            result = order(inputs)

            # `run.end(outputs=result)` fecha explicitamente o run raiz,
            # registrando `result` como a saída final. Fechar explicitamente
            # (em vez de deixar o `with` fechar sozinho ao sair do bloco) é
            # útil quando queremos ter certeza de qual foi o "outputs"
            # final gravado, especialmente em casos mais complexos.
            run.end(outputs=result)

        # Fora do bloco `with trace(...)`, o run já foi encerrado. Se
        # `--send` estava ativo (`client` não é `None`), buscamos e
        # imprimimos a URL pública deste trace no LangSmith.
        if client:
            # `str(run.id)` converte o UUID do run para texto (a função
            # `show_trace` espera uma string). `run.start_time` é passado
            # para acelerar a localização do run no backend do LangSmith.
            show_trace(client, args.project, str(run.id), start_time=run.start_time)

        # Imprime o resultado no terminal, independentemente de termos
        # enviado ou não o trace (isso funciona mesmo em modo 100% local).
        print(result)

        # Salva um arquivo JSON local com o resultado e o "endereço
        # completo" do run (projeto + horário de início + id). O
        # laboratório seguinte (04, sobre feedback) vai LER este arquivo
        # para saber a qual run anexar uma nota — por isso salvamos tudo
        # que for necessário para reencontrar esse run mais tarde.
        # `run.start_time.isoformat()` converte o objeto `datetime` em uma
        # string no formato ISO-8601 (ex.: "2026-09-14T10:00:00"), que é
        # texto simples e cabe dentro de um JSON.
        write_json("01-trace.json", {"outputs": result, "run_id": str(run.id), "project": args.project,
                                     "start_time": run.start_time.isoformat(), "sent": args.send})


# --- Ponto de entrada padrão de um script Python --------------------------
# Quando o Python executa um arquivo diretamente (`python 01_....py`), ele
# define automaticamente a variável especial `__name__` como a string
# `"__main__"`. Se este arquivo fosse importado por OUTRO script (com
# `import este_arquivo`), `__name__` teria o nome do módulo, não
# `"__main__"`. Esse `if` é a forma padrão de dizer: "rode a função `main()`
# só quando este arquivo for executado diretamente, não quando for importado
# como biblioteca por outro código".
if __name__ == "__main__":
    main()
