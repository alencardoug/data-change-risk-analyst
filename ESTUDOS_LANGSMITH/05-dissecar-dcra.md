# 05 · Do resultado ao nó: três análises sob o microscópio

[Índice](README.md) · [Anterior](04-primeiro-trace.md) · [Próximo](06-threads-checkpoints-revisao.md)

**Objetivo:** usar o trace para explicar três caminhos do grafo real. Tempo: 30–40 minutos. Código: [02_dcra.py](labs/02_dcra.py) e [build.py](../src/dcra/graph/build.py).

Este lab instancia `GraphDeps` com interpretação e recomendação de fixture, catálogo em memória e o grafo do produto. **As regras e o workflow são reais; a geração é substituída.** O checkpointer em memória permite pausa/retomada dentro do mesmo processo. Não há consulta ao Postgres nem persistência de `AnalysisRecord` em banco neste laboratório.

## Experimento A — LOW

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case low --send
```

Abra a URL impressa. Entrada: `add index on orders(customer_id)`. Resultado esperado: **LOW**, `ADD_INDEX_LOW_RISK`, `AUTO_FINALIZED`, sem pausa.

1. Expanda `interpret`. Veja a operação `ADD_INDEX` e `index_columns=["customer_id"]` no estado resultante.
2. Encontre `collect_asset`, `collect_deps`, `collect_usage`.
3. Compare seus intervalos na timeline. Ser irmãos na árvore mostra a relação hierárquica; **sobreposição temporal** é a evidência visual de concorrência. Operações de fixture muito rápidas podem tornar isso difícil de enxergar.
4. Abra `assess_risk`, depois [assess](../src/dcra/rules/risk.py). O catálogo registra 90 leituras/dia para `customer_id`; a regra de contenção do índice usa limiar 100. Neste fixture o fator é LOW.
5. Siga a saída de `recommend` até `finalize`. Não procure uma aprovação humana que esse caminho não exige.

O fan-out ocorre nas arestas de `build_graph`; o reducer de `GraphState.evidence` consolida evidências. A implementação é uma prova estrutural da concorrência planejada; o trace permite observar o comportamento de uma execução.

## Experimento B — MEDIUM

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case medium --send
```

Entrada: `drop column orders.customer_legacy_id`. Espere **MEDIUM**, fatores `REFERENCED_BY_VIEW` e `ACTIVELY_READ`, pausa no portão e `outcome=null`.

Abra as evidências: duas views e o consumidor `cs_lookup`. Vá ao `human_review`. O `__interrupt__` retornado pelo grafo contém o payload para revisão. Isso não é um crash do app; é uma saída prevista do protocolo de execução.

A recomendação fixture diz `DO_NOT_PROCEED`. Observe que o risco MEDIUM foi calculado antes, independentemente dessa frase. Esse detalhe evita confundir **disposition** da recomendação com **risk category** e **outcome** do caso.

## Experimento C — HIGH

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case high --send
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case unknown --send
```

| Caso | Evidência decisiva | Esperado |
|---|---|---|
| `orders.id` | chave primária e foreign key que a referencia | HIGH; revisão humana |
| `orders.legacy_region` | coluna ausente do catálogo fixture | HIGH; `ASSET_NOT_FOUND`; revisão humana |

No segundo caso, não espere investigação só porque o risco é HIGH. Abra `has_evidence_gap`: ativo inexistente não é a lacuna que aciona o investigador. O risco e a decisão de investigar respondem a perguntas distintas.

## A mesma leitura com o modelo do projeto

Após [preparar a conta](03-preparacao.md):

```bash
.venv/bin/python ESTUDOS_LANGSMITH/labs/02_dcra.py --case medium --real --send
```

Agora procure os runs de modelo dentro de `interpret` e `recommend`, com prompt, retorno e uso de tokens quando reportado. O texto final pode variar. As evidências ainda são fixtures; este modo é um laboratório controlado, não réplica de todas as dependências da aplicação publicada.

Também pode abrir a [aplicação publicada](https://analisador-de-risco.web.app). Para rastrear suas execuções, você precisa de acesso ao workspace configurado **no servidor**. Informar uma chave no seu terminal não reconfigura o Cloud Run. O ambiente publicado pode ler metadados de Postgres e diferir do catálogo em memória.

**Conceito LangGraph:** fan-out/fan-in e roteamento por estado. **Utilidade:** leituras independentes e caminhos explicáveis. **Alternativa simples:** três chamadas sequenciais e `if/else`. **Defesa:** a combinação de paralelismo, revisão persistente e loop limitado motiva o grafo; o trace permite verificar a execução dessa estrutura. A integração de tracing é descrita em [observabilidade do LangChain](https://docs.langchain.com/oss/python/langchain/observability).

**Exercício oral:** explique por que HIGH não implica “agente vai investigar” e por que LOW não implica “LLM aprovou”.

## Debugging com traces: de `reads_per_day: 90` até `dataset.py`

O passo 4 do Experimento A afirma que o catálogo registra 90 leituras/dia. Esta seção refaz esse caminho ao contrário e sem privilégio: você só tem o trace do caso LOW aberto no LangSmith, não conhece o código e quer descobrir **quem produziu** o número e **por que ele está no trace**. É o exercício de debugging mais comum com observabilidade — o valor está na tela; a origem, não.

### 1. Localizar a primeira aparição no trace

Na árvore do run `dcra-iniciar`, abra cada nó e compare **Input** e **Output**. `reads_per_day` aparece em vários lugares — no input de `assess_risk`, `recommend` e `finalize`, e no output desses também — porque está no estado do grafo e o estado inteiro é passado adiante. O critério para achar o produtor é: **o primeiro nó em que o valor está no Output e não está no Input.** Esse nó é `collect_usage`. Seu output é:

```json
{
  "evidence": [
    {
      "kind": "DOWNSTREAM_USAGE",
      "key": "ops_dashboard",
      "status": "OBTAINED",
      "source": "usage",
      "payload": {
        "consumer": "ops_dashboard",
        "consumer_type": "dashboard",
        "last_read_at": "2026-08-27T09:00:00Z",
        "reads_per_day": 90
      }
    }
  ],
  "step_log": ["collect_usage: 1 item(s)"]
}
```

Anote o que o output entrega de graça além do número: o nome do nó (`collect_usage`), o `kind` (`DOWNSTREAM_USAGE`), o `source` (`"usage"`), a chave (`ops_dashboard`) e o `step_log` **sem** o sufixo `(via MCP)`. Cada um é um termo de busca. Repare também que `collect_usage` não tem filhos: o trace termina no nó. O que aconteceu dentro dele o LangSmith não mostra — daqui em diante a ferramenta é `grep`.

### 2. Do nome do nó à função

```bash
grep -rn "collect_usage" src
```

Descarte `streamlit_app.py` (rótulos de UI) e `build.py` (arestas). Sobra [nodes.py:57](../src/dcra/graph/nodes.py):

```python
def collect_usage(state: GraphState) -> dict:
    sc = state["structured_change"]
    col = _target_column(sc)
    if deps.usage_reader is not None:  # V1: MCP-backed reader (ADR-020)
        items = deps.usage_reader(sc.target_table, col)
        via = " (via MCP)"
    else:
        items = deps.inspect().downstream_usage(sc.target_table, col)
        via = ""
    return {"evidence": items, "step_log": [f"collect_usage{via}: {len(items)} item(s)"]}
```

Há dois ramos, e o trace já disse qual executou: o `step_log` veio como `collect_usage: 1 item(s)`, sem `(via MCP)`, logo `via == ""` e o caminho foi `deps.inspect().downstream_usage(...)`. Isso é debugging com trace no sentido estrito — uma string que o nó gravou no estado descarta metade das hipóteses antes de abrir o próximo arquivo.

### 3. Da interface à implementação

```bash
grep -rn "def downstream_usage" src
```

Três resultados: o `Protocol` em `inspector.py:33`, `DatasetInspector` em `inspector.py:48` e `PostgresInspector` em `warehouse.py:177`. Qual foi instanciado? `deps.inspect()` está em [deps.py](../src/dcra/graph/deps.py):

```python
def inspect(self) -> Inspector:
    return self.inspector or DatasetInspector(self.dataset)
```

`PostgresInspector` só entra quando alguém passa `inspector=`, e `production_deps` só o faz com `DATABASE_URL`. Os metadados do trace dizem que não é esse o caso: `lab: 02-dcra`, `scenario: low`, `model_mode: fixture`, `environment: lab`. Abra [_dcra.py](labs/_dcra.py) → `make_deps`: constrói `GraphDeps(..., dataset=ds)` sem `inspector`. Portanto `DatasetInspector`, que delega para `read_downstream_usage` em [tools.py:81](../src/dcra/evidence/tools.py):

```python
def read_downstream_usage(dataset: Dataset, table: str, column: str) -> list[EvidenceItem]:
    key = f"{table}.{column}"
    if dataset.source_disabled(SOURCE_USAGE):
        return [_unavailable(EvidenceKind.DOWNSTREAM_USAGE, key, SOURCE_USAGE)]
    facts = dataset.get(table, column)
    if facts is None:
        return []
    return [
        EvidenceItem(kind=EvidenceKind.DOWNSTREAM_USAGE, key=u["consumer"],
                     status=EvidenceStatus.OBTAINED, source=SOURCE_USAGE, payload=u)
        for u in facts.usage
    ]
```

Duas coisas fecham o círculo com o JSON do passo 1. `source=SOURCE_USAGE` explica o `"source": "usage"` (a constante mora em `dataset.py:13`). E `payload=u` explica por que o trace mostra o dicionário **inteiro** do consumidor, com `reads_per_day` no nome original: a função não seleciona campos, copia o registro de uso como veio.

### 4. Da função ao dado

`facts` veio de `dataset.get(table, column)` → `Dataset.columns["orders.customer_id"]` → `default_dataset()` em [dataset.py](../src/dcra/evidence/dataset.py):

```python
# for ADD_INDEX scenarios (index target column, low blast radius)
"orders.customer_id": ColumnFacts(
    data_type="bigint",
    is_nullable=False,
    row_estimate=1_800_000,
    dependencies=[],
    usage=[
        {"consumer": "ops_dashboard", "consumer_type": "dashboard",
         "last_read_at": "2026-08-27T09:00:00Z", "reads_per_day": 90},
    ],
),
```

Linha 107. O 90 é um literal, escrito por quem montou a fixture. Resposta à pergunta original: **o número não foi medido; foi escolhido para ficar abaixo do limiar `_INDEX_CONTENTION_RPD = 100` de [risk.py](../src/dcra/rules/risk.py) e manter o caso LOW.** Se alguém alterasse a fixture para 100, `assess_risk` passaria a emitir `INDEX_BUILD_CONTENTION` e o Experimento A deixaria de ser LOW — sem nenhuma mudança em regra ou grafo.

Existe um atalho: `grep -rn '"reads_per_day": 90' src` ou `grep -rn ops_dashboard src` chega a `dataset.py` em um passo. Ele funciona aqui porque o valor é um literal no repositório. Contra `PostgresInspector` ou o leitor MCP ele não acharia nada, e o caminho longo seria obrigatório — até o ponto em que o código faz a consulta, e daí para o banco. Aprenda o caminho longo; use o atalho quando houver.

### 5. Verificar a hipótese sem o LangSmith

Antes de declarar o caso encerrado, reproduza o output do nó localmente. Se o JSON coincidir com o do trace, a cadeia está confirmada:

```bash
.venv/bin/python - <<'EOF'
import json, sys
sys.path.insert(0, "ESTUDOS_LANGSMITH/labs")
from _dcra import interpret_fixture, make_deps
from dcra.graph.nodes import make_nodes
nodes = make_nodes(make_deps())
sc = interpret_fixture("add index on orders(customer_id)")
out = nodes["collect_usage"]({"structured_change": sc})
print(json.dumps([e.model_dump(mode="json") for e in out["evidence"]], indent=2))
EOF
```

Isso chama exatamente o nó que o trace mostrou, com as mesmas dependências do lab, e não envia nada a lugar nenhum.

### 6. Onde o código "manda" isso para o LangSmith

Procure `langsmith` ou `traceable` em `src/dcra`: não há. [config.py](../src/dcra/config.py) só lê o flag `LANGSMITH_TRACING`. Nenhuma linha do produto diz "envie `reads_per_day`". O envio é consequência de três decisões, em três lugares:

**(a) Ligar o tracing — [_common.py](labs/_common.py).** `configure()` define `LANGSMITH_TRACING=true` **apenas** com `--send`, e `session()` abre um `tracing_context(enabled=args.send, client=client, project_name=..., tags=["estudo", lab], metadata={...})`. Sem isso, o mesmo código roda e nada sai da máquina. É daí que vêm os metadados `lab`, `environment` e `synthetic` do trace: foram fixados no contexto, não em cada nó.

**(b) O grafo é um Runnable — [02_dcra.py](labs/02_dcra.py) e [build.py](../src/dcra/graph/build.py).** `build_graph` devolve `g.compile(...)`, um Runnable do LangChain. `graph.with_config(run_name="dcra-iniciar", run_id=root_id, metadata=metadata)` nomeia o run raiz; `compiled.invoke(initial, config=config)` em `run()` executa. Com tracing ligado, o LangChain anexa o callback `LangChainTracer` e o LangGraph reporta cada nó como run filho, com o estado recebido como **Input** e o dicionário retornado como **Output**. Portanto a linha que decide que `reads_per_day` vai para o LangSmith é o `return {"evidence": items, ...}` de `nodes.py:66` — não por conhecer o LangSmith, mas porque é o valor de retorno do nó, e o tracer captura valores de retorno. O `EvidenceItem` é um modelo Pydantic; o SDK o serializa como `model_dump()`, e é assim que o `payload` vira o JSON que você viu.

**(c) O que está no estado viaja — [state.py](../src/dcra/graph/state.py).** `evidence: Annotated[list[EvidenceItem], merge_evidence]`: o reducer concatena e deduplica as evidências dos três coletores. Como o LangGraph passa o estado inteiro ao nó seguinte, `reads_per_day` reaparece nos inputs de `assess_risk`, `recommend` e `finalize`, e no payload de `human_review` (que `review_payload` serializa com `model_dump`). É isso que torna o critério do passo 1 necessário: "está no trace" não significa "foi produzido aqui".

Duas consequências práticas. Primeiro, o trace só tem a granularidade dos nós: `DatasetInspector`, `read_downstream_usage` e `default_dataset` não aparecem porque ninguém os decorou com `@traceable` nem os transformou em Runnable — por isso os passos 3 e 4 precisaram de `grep`. Se quisesse ver `read_downstream_usage` como run filho, o lugar seria um `@traceable` sobre a função ([capítulo 08](08-instrumentacao-contexto.md)); a versão `@tool` em `make_evidence_tools` já aparece como run quando o investigador a chama no modo `--real`. Segundo, o que o nó devolve é o que sai da máquina: `payload=u` copia o registro inteiro. Em fixture é inofensivo; com fonte real, é o ponto onde um campo sensível entraria no trace sem ninguém pedir — tema do [capítulo 19](19-privacidade-amostragem.md).

## Levar para outros projetos — e onde o seu julgamento decide

O que este capítulo treina é **ir do resultado ao nó e do nó ao código** em três caminhos distintos do mesmo grafo. A plataforma de atendimento tem exatamente essa estrutura, com outros nomes.

**Na plataforma de atendimento (Langfuse Cloud).** Os "experimentos A, B e C" do N5 são os três caminhos de `maybe_open_autonomous_window()`: **reaproveitar `ANSWER`** (geração fundamentada entregue verbatim), **guided booking** (trigger elegível, ofertas e parser ordinal vs. embedding) e **fallback livre** (`status != "ANSWER"` ou atalho clínico abaixo de 0,40 → `generate_ungoverned_reply()`, que **não** recebe evidências). Para cada um, faça o que fez com LOW/MEDIUM/HIGH: abra o trace, ache `autonomy.decision`, leia `n5_path` e `fallback_reason`, e vá ao código confirmar por que aquele ramo disparou. As armadilhas são as mesmas: "HIGH não implica investigação" vira "saudação não é fallback até o trace confirmar o ramo"; "disposition ≠ risk category ≠ outcome" vira "status da geração ≠ caminho N5 ≠ mecanismo efetivo (`ungoverned_n5` vs. `governed_autonomy`)" — o ramo governado N3/N4 é avaliado **antes**, e classificar tudo como N5 porque o switch está ligado é o erro equivalente a "LLM aprovou". A sobreposição temporal dos coletores tem paralelo na recuperação: `retrieve()` mistura Q&A e clínico por distância, dedupa pais e corta em `top_k=8` — o trace mostra o resultado; o código explica a ordem.

**Em projetos comuns do ecossistema.** Todo grafo LangGraph com roteamento condicional merece este exercício: um caso por aresta condicional, executado com dependências falsas, com o trace guardado. É a forma mais barata de documentar "por que este caminho existe" e de detectar quando uma mudança de prompt muda o roteamento sem ninguém perceber. Em Langfuse, marque o caminho como score categórico (o projeto usa `n5.path`) — assim a distribuição de caminhos vira um gráfico, e uma mudança na distribuição vira um alerta.

**O fator humano — onde a IA faz e onde você decide.** Um assistente segue o trace e explica cada nó com precisão: "o roteador leu `risk == HIGH` e chamou `human_review`". É uma boa narração. O que só você faz é **julgar se o caminho estava certo para aquele caso** — e isso exige saber o que o pedido queria dizer. No DCRA, "remover `orders.id`" é HIGH porque você sabe o que é uma chave primária; na plataforma, "quanto custa a consulta com o oncologista?" caindo em fallback livre é um erro porque você sabe que existe uma tabela de preços que deveria ter sido recuperada. A IA vê ramos; você vê intenção. Foque nos casos em que o trace está "verde" e o caminho está errado — são os que nenhum filtro de erro vai mostrar, e os que um leitor automático descreve com naturalidade como se fossem corretos.
