# 01_trace_python.py e _common.py — o que acontece entre o código e a tela do LangSmith

Companheiro de leitura de [01_trace_python.py](01_trace_python.py) e [_common.py](_common.py).
Complementa o capítulo [04 · Seu primeiro trace](../04-primeiro-trace.md), que ensina *o que olhar*;
este documento explica *por que aquilo aparece*. Tudo aqui foi cruzado em 2026-09-11 com:

- o workspace real em https://smith.langchain.com (projeto `dcra-estudos`, três execuções do lab 01
  às 20:30, 20:42 e 20:59 BRT, todas com raiz `pedido-restaurante`);
- o código-fonte do SDK instalado (`langsmith==0.12.4`, em `.venv/lib/python3.13/site-packages/langsmith`).

Quando eu afirmar "o SDK faz X", é porque li a função correspondente; o caminho fica indicado para
você conferir quando a versão mudar.

---

## 1. A ideia central em um parágrafo

Tracing no LangSmith é **uma árvore de runs enviada por HTTP em background**. Cada run tem nome,
tipo, inputs, outputs, tags, metadata, hora de início/fim e um pai (ou nenhum, se for a raiz).
O SDK não "espiona" o seu programa: ele só cria um run quando o código passa por um ponto instrumentado
(`@traceable` ou `with trace(...)`), e só descobre quem é o pai de quem porque guarda, em uma variável
de contexto do Python (`contextvars`), qual run está "aberto" no momento. Sem esse contexto ativo, os
decoradores existem, mas não geram nada. O `_common.py` é a parte do curso que decide **se** o contexto
existe (`--send`), **para qual projeto** ele aponta e **quais rótulos** todo run vai carregar.

---

## 2. Vocabulário que a tela usa (e o código também)

| Termo | O que é | Onde aparece no lab 01 |
|---|---|---|
| **Run** | Uma operação registrada: nome + tipo + inputs + outputs + tempos | `pedido-restaurante`, `consultar_cardapio`, `calcular_total` |
| **Trace** | O conjunto de runs de uma mesma raiz; identificado pelo `trace_id` | A árvore de três nós |
| **Root run** | Run sem pai. Para ela, `trace_id == run_id` | `pedido-restaurante` |
| **Child run** | Run criada enquanto outra estava aberta | as duas funções decoradas |
| **run_type** | Rótulo semântico: `chain` (padrão), `tool`, `llm`, `retriever`, `prompt`, `parser`, `embedding` | `tool` em `consultar_cardapio`; `chain` nas outras |
| **Tags** | Lista de strings, herdada pelos filhos, boa para filtrar | `estudo`, `01-python` |
| **Metadata** | Dicionário chave→valor, herdado pelos filhos, bom para filtrar e agrupar | `environment`, `lab`, `synthetic`, `scenario` |
| **Project** (tracing project) | A "pasta" onde os traces caem; criada na primeira ingestão | `dcra-estudos` |
| **dotted_order** | String `AAAAMMDD…Z<id>.AAAAMMDD…Z<id>` que codifica caminho e ordem na árvore | invisível na UI, é o que ordena os filhos |
| **post / patch** | Os dois envios de cada run: um ao abrir (`post`) e um ao fechar (`patch`) | ver §6 |
| **flush** | Esvaziar a fila de envio em background antes de o processo morrer | `client.flush(timeout=10)` |

---

## 3. `01_trace_python.py`, linha a linha

### 3.1 `@traceable` — a "função sobre a função"

```python
@traceable(run_type="tool", name="consultar_cardapio")
def menu(item: str) -> dict:
    return {"item": item, "preco_reais": 18, "disponivel": True}
```

`traceable` é um decorador: ele recebe `menu` e devolve **outra função** com o mesmo nome e a mesma
assinatura, que passa a ser chamada no lugar da original. O que essa função de fora faz a cada chamada
(`run_helpers.py`, função interna `_setup_run`):

1. **Pergunta ao contexto se tracing está ligado** (`utils.tracing_is_enabled`). A ordem de precedência
   é: `tracing_context(enabled=...)` → "existe um run aberto?" → `ls.configure(...)` global →
   variáveis de ambiente `LANGSMITH_TRACING` / `LANGCHAIN_TRACING_V2`. Se der falso, chama a função
   original e devolve o resultado. **Custo praticamente zero; nenhuma rede.**
2. **Captura os inputs pela assinatura**: usa `inspect.signature(menu).bind_partial(*args, **kwargs)`.
   É por isso que a UI mostra `item: risoto-de-dados` — o nome do argumento vira a chave. Se você
   renomear o parâmetro, a chave na tela muda; se passar um objeto não serializável, o SDK tenta
   converter e, no pior caso, registra um marcador de falha em vez de derrubar o seu programa.
3. **Procura o run pai** na variável de contexto. Achou (`pedido-restaurante` está aberto) → cria um
   filho com `parent_run.create_child(...)`. Não achou → cria uma raiz nova.
4. **Monta tags e metadata herdando do contexto**: `tags = tags_do_decorador + tags_do_contexto`;
   `metadata = {**metadata_do_contexto, **metadata_do_decorador, "ls_method": "traceable"}`. É esse
   `ls_method: traceable` que você vê na aba *Attributes* do filho — e `ls_method: trace` na raiz.
5. Envia o `post` (início), **executa a função original**, guarda o retorno como `outputs`
   (ou a exceção como `error`) e envia o `patch` (fim).

O que **não** acontece: o decorador não sabe quem chamou a função, não lê variáveis locais, não vê
`order()`. `order()` não é decorada, então é invisível na árvore — e ainda assim os dois filhos ficam
debaixo da raiz certa. **A hierarquia vem do contexto de execução, não da pilha de chamadas.** Isso é o
que permite instrumentar só o que importa e deixar o encanamento fora da tela.

Sobre os argumentos:

- `name="consultar_cardapio"`: sem ele, o run se chamaria `menu` (nome da função). Nomes estáveis e
  em linguagem de negócio são o que você vai filtrar em produção; refatorar a função não deve mudar o nome.
- `run_type="tool"`: muda o ícone e permite `eq(run_type, "tool")` em consultas (lab 16). Não muda o
  comportamento. Como o capítulo 04 insiste: um span `tool` aqui foi chamado por Python, não por um
  agente — o tipo é uma **declaração sua**, não uma prova de decisão do modelo.
- `calcular_total` sem `run_type` → `chain`, o padrão do SDK.

### 3.2 `with trace(...)` — a raiz explícita

```python
with trace("pedido-restaurante", inputs=inputs, metadata={"scenario": "pedido-valido"}) as run:
    result = order(inputs)
    run.end(outputs=result)
```

`trace` é a classe `run_helpers.trace`, usável como context manager. Ao entrar (`_setup`):

- cria um `RunTree` com `run_type="chain"` (padrão), `id` novo (UUID v7 — repare que os ids na URL
  começam com o timestamp, `01a092e9-…`), `start_time = agora`, `trace_id = id` (é raiz);
- monta `dotted_order` a partir de `start_time` + `id` — é a chave de ordenação e de endereço no SmithDB;
- mescla tags/metadata: `tags = sorted(set(minhas + contexto))`;
  `metadata = {**minhas, **contexto, "ls_method": "trace"}` — **aqui o contexto vence** em caso de
  colisão de chave (o oposto de `traceable`, onde a metadata do decorador vence). Não é um problema
  hoje, mas se um dia você passar `metadata={"lab": ...}` no `trace()`, o valor do `session()` prevalece;
- se tracing está ligado: `run.post()` (vai para a fila) e **publica este run como "pai atual"** no
  contexto. É esse passo que faz `menu()` e `total()` virarem filhos.

Por que o `run.end(outputs=result)` é explícito? Porque o `with` não sabe o que é "a saída" do bloco.
`end()` grava `outputs` e `end_time`; ao sair do `with`, `_teardown` faz o `patch()` com esses campos.
Se o bloco lançar exceção, `_teardown` chama `end(error=traceback)` e ainda assim faz o `patch` — o
run aparece vermelho na tela, com o stack trace. (O lab 03 explora isso.)

Depois do `with`, o objeto `run` continua existindo: `run.id` e `run.start_time` são lidos para
`show_trace` e para o `01-trace.json`. **Isso vale mesmo sem `--send`**: o `RunTree` é criado de
qualquer forma, só não é enviado. É por isso que o artefato gerado em modo local tem um `run_id`
perfeitamente válido que **não existe no servidor** — daí o campo `"sent"` no JSON e a checagem que o
lab 04 faz antes de tentar anexar feedback.

### 3.3 `show_trace` e `write_json` — o endereço do run

O run não é endereçado só pelo id. Em `show_trace`, `client.runs.get_url(run_id, project_id=…,
trace_id=…, start_time=…)` pede ao servidor a URL, informando **projeto + trace + run + hora de
início**. O `start_time` é opcional, mas acelera a busca (o armazenamento é particionado por tempo).
Como a raiz tem `trace_id == run_id`, o script passa o mesmo valor nos dois.

`write_json("01-trace.json", …)` grava exatamente esse trio (mais `sent`) para que o lab 04 consiga
fazer `create_feedback(run_id, session_id=project.id, trace_id=run_id, start_time=…)`. Tudo que
precisa "voltar" a um run no LangSmith atual carrega esse endereço completo, não só o UUID.

Os métodos `client.runs.*` são a API v2 do SDK (assíncrona). `asyncio.run(...)` executa a corrotina
dentro do script síncrono. As três tentativas com `sleep` crescente existem porque, logo após o
`flush`, o run pode ainda não estar consultável (ingestão em lote — ver §6).

---

## 4. `_common.py` — a dinâmica que o lab 01 herda

### 4.1 `parser()` — envio é uma decisão, não um efeito colateral

`--send` liga o envio; `--project` escolhe o destino, com padrão `DCRA_LAB_PROJECT` ou `dcra-estudos`.
A ausência de `--send` é o modo padrão. Isso inverte a convenção do SDK, em que a simples presença de
`LANGSMITH_TRACING=true` no ambiente já envia tudo — e que é a fonte clássica do acidente "traces de
teste no projeto de produção".

### 4.2 `configure()` — a ordem das linhas é o conteúdo

```python
enabled = "true" if args.send else "false"
os.environ["LANGSMITH_TRACING"] = enabled
os.environ["LANGCHAIN_TRACING_V2"] = enabled
load_dotenv(ROOT / ".env", override=False)
os.environ["LANGSMITH_PROJECT"] = args.project
```

Quatro fatos tornam essa ordem obrigatória:

1. **O `.env` do produto diz o contrário.** Segundo `.env.example`, ele traz `LANGSMITH_TRACING=true`
   e `LANGSMITH_PROJECT=dcra` (o projeto do app, que hoje tem 183 traces/7d no seu workspace). Se o
   lab carregasse o `.env` primeiro, uma execução sem `--send` enviaria traces sintéticos para o projeto
   do produto.
2. **`load_dotenv(override=False)` não sobrescreve o que já está em `os.environ`.** Logo, escrever
   `LANGSMITH_TRACING` *antes* de carregar o `.env` faz a flag do laboratório vencer, enquanto tudo o
   mais do `.env` (chave da API, endpoint, provedor de LLM) entra normalmente.
3. **`LANGSMITH_PROJECT` é escrito *depois*, sem condição.** O nome do projeto não é uma preferência do
   `.env`; é o argumento do lab. `get_env_var("PROJECT")` do SDK procura `LANGSMITH_PROJECT` e depois
   `LANGCHAIN_PROJECT`, então sobrescrever o primeiro basta.
4. **O SDK lê variáveis de ambiente uma vez por processo.** `utils.get_env_var` e
   `utils.get_tracer_project` têm `@functools.lru_cache`. Qualquer `os.environ[...] = ...` feito
   *depois* da primeira leitura é ignorado. É por isso que `configure()` roda antes de o
   `langsmith.Client` ser criado, e por isso o comentário "definido ANTES de `dcra.config`
   importar/carregar `.env`": `src/dcra/config.py` chama `load_dotenv()` no import, e o `_common.py`
   só importa `dcra.*` dentro de `real_model()`, tarde o suficiente.

Os dois nomes de flag: `LANGCHAIN_TRACING_V2` é o nome legado; `LANGSMITH_TRACING` é o atual. O SDK
consulta `TRACING_V2` primeiro e `TRACING` como fallback (`tracing_is_enabled`). Setar os dois garante
o mesmo resultado em qualquer versão e em qualquer biblioteca que ainda leia o nome antigo.

`credential_present` só verifica que a chave não está vazia nem é placeholder (`...`, `<...>`). A
autenticação real acontece no primeiro envio — "configurada" ≠ "válida".

### 4.3 `session()` — o contrato de todos os labs

```python
with tracing_context(
    enabled=args.send,
    client=client,
    project_name=args.project,
    tags=["estudo", lab],
    metadata={"environment": "lab", "lab": lab, "synthetic": True},
):
    yield client
```

`tracing_context` grava esses valores nas variáveis de contexto do SDK e as restaura ao sair. Cada campo
resolve um problema:

- **`enabled=args.send`** — redundante com as variáveis de ambiente, de propósito. O contexto tem
  precedência sobre o ambiente (`tracing_is_enabled` checa `tc["enabled"]` primeiro). Se algum código
  ou biblioteca mudar `LANGSMITH_TRACING` no meio do caminho, o lab continua obedecendo ao `--send`.
- **`client=client`** — o `Client()` só é instanciado com `--send`. Sem ele, nenhum objeto com fila de
  envio, thread em background ou leitura de chave é criado. `yield client` devolve `None` no modo local,
  e os labs usam `if client:` como "estou conectado?".
- **`project_name=args.project`** — terceiro lugar onde o projeto é fixado (env, contexto, e o `Client`
  também herdaria do env). `_get_project_name` prefere o contexto.
- **`tags=["estudo", lab]`** — ver §4.4.
- **`metadata={...}`** — ver §4.4.
- **`finally: client.flush(timeout=10)`** — ver §6. Sem isso, o processo poderia terminar com runs
  ainda na fila.

### 4.4 A tag `lab` e a metadata: por que rotular na infraestrutura, não em cada script

Cada lab chama `session(args, lab="01-python")`, `lab="04-feedback"` etc. O valor entra **duas vezes**:
como tag (`01-python`) e como metadata (`lab: 01-python`). Não é redundância acidental:

- **Tags** são a forma mais barata de filtrar na UI e na API: `has(tags, "01-python")`. A UI mostra
  chips; a busca "Full text" que usei no site gerou o filtro `and(eq(is_root, true), search("…"))`, a
  mesma linguagem que os labs 16/17 escrevem à mão em `runs.query(filter=...)`.
- **Metadata** é chave→valor: permite `eq(metadata_key, "lab")`-style, agrupamento em dashboards, e
  entra em datasets/experimentos quando um run é promovido a exemplo. `environment=lab` é o mesmo
  padrão que, em produção, seria `environment=prod`; `synthetic=true` é uma promessa para qualquer
  evaluator ou exportação futura: "não trate isto como comportamento real".
- **Herança**: tudo que está em `tracing_context` é copiado para a raiz e, de lá, para cada filho.
  `consultar_cardapio` mostra as mesmas tags e a mesma metadata de `pedido-restaurante` sem que o
  decorador tenha declarado nada. Rotular uma vez, na sessão, é o que garante que **nenhum run fique
  sem rótulo** — inclusive os que o SDK ou o LangChain criam por conta própria.
- **Rastreabilidade entre labs**: o lab 04 anexa feedback ao run do lab 01, mas o faz sob
  `lab="04-feedback"`. Se um dia houver runs criados pelo lab 04 (não há hoje), eles serão distinguíveis.
  A tag `estudo` é o guarda-chuva: um filtro `has(tags, "estudo")` separa todo o curso do resto.

A regra geral que vale para outros projetos: **rótulos de ambiente, versão e finalidade pertencem à
inicialização do processo (uma vez), não a cada ponto instrumentado.** Os pontos instrumentados
adicionam só o que é específico deles (`scenario: pedido-valido` no `trace()`).

### 4.5 `manifest()` — reprodutibilidade fora do LangSmith

`manifest()` calcula SHA do git, sujeira da árvore, versão de Python e dos pacotes, e SHA-256 dos
arquivos que influenciam um resultado (labs, evals, `src/dcra`, dados, `uv.lock`, `pyproject.toml`).
**Nada disso vai para o LangSmith** — é gravado em `artefatos/manifesto.json` (lab 00) e dentro de
`06-*.json` (lab 06), e o lab 12 compara hashes para decidir se um baseline ainda é válido.

Ele tem um irmão no servidor: o SDK envia sozinho `revision_id`, obtido com
`git describe --tags --always --dirty` (`env/_runtime_env.py::_get_default_revision_id`). No seu
workspace, os três traces do lab 01 mostram `revision_id: 9331fb5-dirty` — o commit anterior ao
`9f3ccda` de hoje, com árvore suja no momento do envio. Se você quiser controlar esse valor
(por exemplo, em CI), `LANGCHAIN_REVISION_ID=<valor>` tem precedência.

### 4.6 `require_real()` / `real_model()` — não usados aqui, mas explicam o desenho

O lab 01 não chama modelo nenhum. Essas funções existem para os labs 02/07/08: `--real` é uma segunda
trava explícita (além de `--send`), e `real_model()` reutiliza `dcra.llm.factory.build_chat_model`
do produto — importado só nesse momento, pelos motivos do §4.2.

---

## 5. O que o SDK e o servidor acrescentam sem você pedir (tudo visto na aba *Attributes*)

Ao enfileirar cada run, `Client._insert_runtime_env` mescla dois blocos em `extra`:

**`runtime`** (`get_runtime_environment()`): `sdk: langsmith-py`, `sdk_version: 0.12.4`,
`library: langsmith`, `platform: Linux-7.1.1-…`, `runtime: python`, `py_implementation: CPython`,
`runtime_version: 3.13.14`, `langchain_version: 1.3.18`, `langchain_core_version: 1.6.1`, e qualquer
SHA de release que plataformas de CI/CD exportem (`GITHUB_SHA`, `CI_COMMIT_SHA`, `VERCEL_GIT_COMMIT_SHA`…).
Isso é o que permite, num incidente, saber *de qual build* veio um trace.

**`metadata`** (`get_langchain_env_var_metadata()`): **toda variável de ambiente que comece com
`LANGCHAIN_` ou `LANGSMITH_`**, exceto uma lista fixa (`LANGCHAIN_API_KEY`, `LANGCHAIN_ENDPOINT`,
`LANGCHAIN_TRACING_V2`, `LANGCHAIN_PROJECT`, `LANGSMITH_RUNS_ENDPOINTS`, …) e exceto nomes que
contenham `key`, `secret`, `token`, `password`, `credential`, `email`. Sobrou, no seu caso:
`LANGSMITH_PROJECT: dcra-estudos` e `LANGSMITH_TRACING: true` — é o grupo "LangSmith" da tela.
Mais `revision_id`, tratado acima.

Duas consequências práticas:

- **Privacidade por convenção de nome.** Uma variável `LANGSMITH_CUSTOMER_DB=…` seria enviada em cada
  run. Se precisar guardar algo sensível com esse prefixo, use um nome que contenha `SECRET`/`TOKEN`,
  ou desligue com `Client(omit_traced_runtime_info=True)`. Para esconder conteúdo:
  `LANGSMITH_HIDE_INPUTS=true`, `LANGSMITH_HIDE_OUTPUTS=true`, `LANGSMITH_HIDE_METADATA=true`
  (lab 10 trata disso com mais nuance).
- **Metadata sua vence a do ambiente.** `_insert_runtime_env` só adiciona chaves que ainda não existem.

Há ainda um campo que **não** está no SDK: `ls_run_depth: 0` na raiz. Ele é calculado pelo servidor
(SmithDB) a partir do `dotted_order`. Se um dia você procurar essa chave no código-fonte e não achar,
é por isso.

---

## 6. Ciclo de vida de rede: `post`, `patch`, fila, `flush`

1. `trace.__enter__` → `RunTree.post()` → `Client.create_run` → entra numa `PriorityQueue`
   (`auto_batch_tracing=True` por padrão). Uma thread em background agrupa runs e envia em lote
   (`/runs/batch` ou `/runs/multipart`).
2. Cada `@traceable` faz o mesmo `post` na entrada e um `patch` (`Client.update_run`) na saída, com
   `outputs`, `end_time` e `error`.
3. `trace.__exit__` → `patch` da raiz.
4. `client.flush(timeout=10)` no `finally` de `session()`: espera a fila esvaziar até 10 s. Também é
   chamado no início de `show_trace`, porque a URL só faz sentido se o run já saiu do processo.
5. Do lado do servidor, a ingestão é assíncrona: por isso `show_trace` tenta três vezes, e por isso o
   capítulo 03 avisa "trace aparece segundos depois".

Cada run da árvore, portanto, gera **dois** registros de rede. A raiz tem inputs no `post` e outputs
no `patch`; se você abrir a UI no meio de uma execução longa, verá runs "em andamento" (sem output).
Um processo que morre antes do `flush` perde os `patch`es pendentes — o run fica eternamente
"pending" na tela. É a linha "script antigo perde os últimos spans" da tabela de sintomas do capítulo 03.

Amostragem: `LANGSMITH_TRACING_SAMPLING_RATE` (0–1) decide, **por trace_id**, se uma árvore inteira é
enviada — nunca metade de uma árvore. Não está ligada no lab; vale saber que existe antes de estranhar
um projeto "com buracos" em produção.

---

## 7. Código → tela: a tabela cruzada com o seu workspace

| No código | Na UI (`dcra-estudos` → `pedido-restaurante`, 20:59) |
|---|---|
| `parser()` → `--project` default | Projeto **dcra-estudos** em *Tracing* (16 traces/7d; os 6 % de erro são do lab 03) |
| `trace("pedido-restaurante", inputs=…)` | Run raiz, ícone de chain, aba *Input*: `item`, `quantidade` |
| `run.end(outputs=result)` | Aba *Output*: `total_reais: 36`, `moeda: BRL` |
| `metadata={"scenario": "pedido-valido"}` | *Attributes → Metadata → scenario* |
| `@traceable(run_type="tool", name="consultar_cardapio")` | Filho com tooltip **Tool**, `ls_method: traceable` |
| `@traceable(name="calcular_total")` | Filho com ícone de chain (tipo padrão) |
| `order()` (sem decorador) | **Não aparece** — e os filhos ainda assim pendem da raiz |
| `session(tags=["estudo", lab])` | Chips `01-python`, `estudo` — iguais na raiz e nos filhos |
| `session(metadata={...})` | `environment: lab`, `lab: 01-python`, `synthetic: true` |
| `configure()` → `os.environ[...]` | Grupo *LangSmith*: `LANGSMITH_PROJECT`, `LANGSMITH_TRACING` |
| (SDK) `git describe --dirty` | `revision_id: 9331fb5-dirty` |
| (SDK) `get_runtime_environment()` | Grupo *Runtime*: `sdk_version 0.12.4`, `langchain_version 1.3.18`, `runtime_version 3.13.14`… |
| (servidor) | `ls_run_depth: 0` |
| `run.id` (raiz) | URL `…&peek=<id>&peeked_trace=<mesmo id>&start_time=…` — `trace_id == run_id` |
| filho | URL `…&peek=<outro id>&peeked_trace=<id da raiz>` |
| lab 04 `create_feedback(key="lab_total_correto")` | Aba *Feedback* da raiz: `lab_total_correto 1.00` |
| busca "Full text" na UI | filtro `and(eq(is_root, true), search("risoto-de-dados"))` — sintaxe dos labs 16/17 |

---

## 8. Três processos, três projetos

O mesmo `.env` alimenta três programas com destinos diferentes — e é o `_common.py` quem impede que
se misturem:

| Processo | Como o tracing é decidido | Projeto |
|---|---|---|
| App (`dcra`) | `Settings.from_env()` lê `LANGSMITH_TRACING` do `.env` (`true` por padrão, ADR-013) | `dcra` local; `dcra-prod` no Cloud Run |
| Labs | `configure()` impõe `--send`; `.env` só contribui a chave | `dcra-estudos` (ou `--project`) |
| Testes | `tests/conftest.py`, fixture `autouse` → `LANGSMITH_TRACING=false` | nenhum |

Você viu os cinco projetos na lista: `dcra-estudos`, `evaluators` (experimentos dos labs 06/08),
`dcra-estudos-custos-sinteticos` (lab 09), `dcra` e `dcra-prod`. A separação é toda por nome de
projeto — a mesma chave, o mesmo workspace. Isso é conveniente e é também o risco: nada no servidor
impede um script mal configurado de escrever em `dcra-prod`.

---

## 9. Armadilhas observadas nesta sessão

1. **Artefato sobrescrito por execução local.** `artefatos/01-trace.json` está com `"sent": false` e
   um `run_id` de 21:10 BRT, posterior aos três envios. Quem rodar o lab 04 agora recebe "O trace salvo
   é local". A causa provável: `verificar_material.py` executa todos os labs em modo local (linha
   `(["01_trace_python.py"], 0)`) e, portanto, **sobrescreve o artefato toda vez que roda**. Solução:
   `01_trace_python.py --send` de novo antes do lab 04. Lição: o *último* run é o que fica no
   artefato; o modo local também gera ids válidos (§3.2).
2. **`revision_id` com `-dirty`.** Todos os traces enviados hoje carregam esse sufixo. Para
   experimentos que você vai comparar (labs 06/13), envie com árvore limpa ou fixe
   `LANGCHAIN_REVISION_ID`.
3. **Ordem de tags na lista.** A linha das 20:30 mostrava `estudo, 01-python` e as outras
   `01-python, estudo`; `trace._setup` ordena (`sorted(set(...))`), `traceable` não. Não dependa da
   ordem; filtre por `has(tags, …)`.
4. **Precedência assimétrica de metadata.** Em `trace()`, a metadata do contexto vence a do run; em
   `@traceable`, a do decorador vence. Evite repetir chaves entre os dois níveis.
5. **`lru_cache` nas variáveis de ambiente.** Mudar `os.environ` depois do primeiro `Client()` ou da
   primeira chamada instrumentada não tem efeito no mesmo processo. Em testes que trocam projeto,
   use `tracing_context(project_name=…)`, não `os.environ`.
6. **Banner "Legacy API usage detected"** no topo do site: a migração dos labs para a API v2
   (`client.runs.*`) foi feita hoje no commit `9f3ccda`; os traces que você vê ainda são do
   `9331fb5`. Depois de rodar os labs de novo, o aviso deve parar de ser alimentado por eles.

---

## 10. Checklist para configurar um projeto novo (o que este lab ensina de reutilizável)

- [ ] Decidir envio por **flag explícita** (`--send`, `TRACING_ENABLED=false` versionado), nunca pela
      presença da chave.
- [ ] Setar `LANGSMITH_TRACING` **antes** de qualquer `load_dotenv`/import que leia ambiente; lembrar
      do `lru_cache`.
- [ ] Um **projeto por finalidade**: produção, desenvolvimento, estudo, e "nenhum" para a suíte de
      testes (`conftest.py`).
- [ ] Um `tracing_context` (ou equivalente) na inicialização com `tags` e `metadata` de
      **ambiente, versão, finalidade** — herdados por tudo.
- [ ] Auditar quais `LANGSMITH_*`/`LANGCHAIN_*` existem no ambiente: elas viajam na metadata de cada run.
- [ ] Nomes de run em linguagem de negócio (`name=`), `run_type` como declaração honesta.
- [ ] `flush()` antes de o processo terminar; timeout definido.
- [ ] Guardar o **endereço completo** de runs que você vai referenciar depois: projeto + `trace_id` +
      `run_id` + `start_time`.
- [ ] Ter um "doctor" que diga o que está configurado sem imprimir valores (`00_doctor.py`).

---

## 11. Perguntas para se fazer sem rodar nada

1. Se `total()` lançasse `ZeroDivisionError`, o que apareceria em cada um dos três nós? (Filho com
   `error`; raiz também com `error`, porque a exceção atravessa o `with`; `consultar_cardapio` verde.)
2. Se você trocasse `with trace(...)` por `@traceable` em `order()`, o que mudaria na tela? (Nada de
   visível na árvore; `ls_method` passaria a `traceable`; `inputs` viriam como `{"inputs": {...}}`,
   o nome do parâmetro; e você perderia o `run.end(outputs=…)` explícito — o retorno vira output.)
3. Onde a tag `01-python` é definida? (Em nenhum lugar de `01_trace_python.py`: vem do argumento
   `lab=` passado a `session()`.)
4. Por que o filho não tem `scenario` diferente da raiz? (Porque `trace()` publica sua metadata
   mesclada no contexto, e `traceable` herda dela — `scenario` também desce para os filhos.)
5. O que acontece se `LANGSMITH_API_KEY` estiver errada e `--send` for usado? (`configure()` passa,
   `Client()` é criado, o `post` vai para a fila, a thread em background recebe 401/403 e loga um aviso;
   o script termina "com sucesso" e `show_trace` imprime o fallback. Autenticação só é testada na rede.)
