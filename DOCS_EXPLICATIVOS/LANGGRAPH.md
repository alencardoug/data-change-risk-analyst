# LANGGRAPH — o que ele faz aqui, e o que mais ele faz

## A analogia rápida

Se LangChain é o "JDBC" (uma interface comum para falar com diferentes LLMs/tools), **LangGraph é
uma máquina de estados** — parecido com um fluxograma de departamento de RH desenhado num quadro
branco: caixas (etapas), setas (o que vem depois), e uma delas é literalmente "espera aprovação do
gerente" — o processo *para*, o papel fica numa gaveta, e só continua quando alguém assina. A
diferença para uma função Python comum chamando outra é que esse fluxograma **pode ter um estado
persistido, pausas reais, ciclos com trava, e ramos que dependem de dados** — coisas que uma
cadeia linear de chamadas (`a() → b() → c()`) não modela bem.

Este projeto é, literalmente, um fluxograma de aprovação de mudança de dado — por isso o LangGraph
não é um acessório, é a espinha dorsal.

---

## Os quatro conceitos, e onde cada um está no código

### 1. Estado tipado — `GraphState`

**Onde**: `src/dcra/graph/state.py:33`.

```python
class GraphState(TypedDict, total=False):
    change_request: ChangeRequest
    evidence: Annotated[list[EvidenceItem], merge_evidence]
    risk_history: Annotated[list[RiskAssessment], append_list]
    ...
```

Um `TypedDict` — um dicionário Python comum, mas com um contrato de campos declarado. Todo nó do
grafo recebe o estado inteiro e devolve **só as chaves que mudou** (um "patch" parcial); o
LangGraph aplica cada patch usando a regra de merge daquele campo.

### 2. Reducers — como dois patches concorrentes viram um só

**Onde**: `merge_evidence` e `append_list` em `state.py:18-30`.

O `Annotated[list[X], minha_funcao]` diz ao LangGraph: "quando dois nós escreverem nesse campo no
mesmo passo, não sobrescreva — chame `minha_funcao(valor_atual, valor_novo)`". Isso é necessário
porque três nós (`collect_asset`, `collect_deps`, `collect_usage`) escrevem em `evidence` **ao
mesmo tempo** (veja fan-out abaixo) — sem um reducer, o último a terminar apagaria os outros dois.
`merge_evidence` concatena, remove duplicatas por `(kind, key)` e **ordena** o resultado — a
ordenação é o detalhe que garante que o mesmo conjunto de evidências sempre produza a mesma lista
final, não importa em que ordem os três nós paralelos terminaram (essencial para a regra de risco
em `REGRAS.md` ser reproduzível). `append_list` é o reducer mais simples possível — só concatena,
usado para históricos (`risk_history`, `recommendations`, `step_log`) onde ordem de chegada não
importa tanto quanto "nunca perder um item".

### 3. Fan-out / fan-in — passos paralelos com sincronização automática

**Onde**: `src/dcra/graph/build.py:36-42`.

```python
g.add_edge("interpret", "collect_asset")
g.add_edge("interpret", "collect_deps")
g.add_edge("interpret", "collect_usage")
g.add_edge("collect_asset", "assess_risk")
g.add_edge("collect_deps", "assess_risk")
g.add_edge("collect_usage", "assess_risk")
```

Três arestas saindo do mesmo nó (`interpret`) = fan-out: os três `collect_*` rodam no mesmo
**superstep** (não em sequência). Três arestas chegando no mesmo nó (`assess_risk`) = fan-in: o
LangGraph só executa `assess_risk` depois que **todos os três** terminaram — você não precisa
escrever nenhuma lógica de sincronização (`asyncio.gather`, threads, locks); é automático porque
está declarado na topologia do grafo.

### 4. Roteamento condicional determinístico

**Onde**: `route_after_assess`, `route_after_recommend`, `route_after_review` em
`src/dcra/graph/nodes.py:198-221`; ligados via `add_conditional_edges` em `build.py`.

```python
def route_after_recommend(state: GraphState) -> str:
    if risk and risk.category == RiskCategory.LOW:
        return "finalize"
    return "review"
```

Uma função pura do estado decidindo o próximo nó. É deliberadamente **não** o LLM decidindo "para
onde vou agora" — veja `REGRAS.md` para o porquê disso importar (auditabilidade). Repare no padrão:
cada `route_*` é testada isoladamente (`tests/unit/test_routing.py`) sem rodar o grafo inteiro nem
gastar uma chamada de modelo.

### 5. `interrupt()` / `Command(resume=...)` — a pausa real

**Onde**: nó `human_review` em `nodes.py:138-153`; retomada em `build.py:92-103`.

```python
raw = interrupt(payload)   # a execução para AQUI, literalmente devolve o controle pro chamador
action = ReviewAction.model_validate(raw)   # só roda quando alguém chama resume()
```

Isso é o coração do projeto. `interrupt(payload)` faz o grafo **parar de executar** e devolver
`payload` para quem chamou `.invoke()` — não é uma exceção, não é um erro, é um "aguardando
entrada" de primeira classe. O estado inteiro até aquele ponto já está salvo no checkpointer
(Postgres, em produção). Depois, uma chamada separada — possivelmente minutos, horas, ou (como no
cenário S8 de `DEMO.md`) depois de um **restart do banco** — retoma exatamente daquele ponto:

```python
compiled.invoke(Command(resume=value), config={"configurable": {"thread_id": thread_id}})
```

A analogia do fluxograma de RH: o processo não fica "vivo" numa thread esperando — ele literalmente
desliga, e uma nova execução, dias depois, começa lendo o estado salvo e continua como se nunca
tivesse parado.

### 6. `thread_id` e o checkpointer — a "fita cassete" do processo

Cada caso tem um `thread_id` (= `ChangeRequest.id` = `analysis_record.id`) que é a chave para toda
a história de estados daquele caso no checkpointer. Em produção isso é o `PostgresSaver`
(`src/dcra/persistence/checkpointer.py`), que grava cada passo nas tabelas `checkpoints`,
`checkpoint_blobs`, `checkpoint_writes` — veja `INFO_BANCO.md` para o schema exato dessas tabelas,
linha por linha, com dados reais. Em testes, é o `MemorySaver` (mesma interface, guarda em RAM,
some quando o processo acaba) — a troca é transparente porque ambos implementam o mesmo contrato
de checkpointer do LangGraph.

### 7. Loop limitado com trava — a revisão

**Onde**: `route_after_review` em `nodes.py:210`; edges `reassess_gate → collect_*` em `build.py`.

O caso pode voltar de `human_review` para `recommend` (nota simples) ou para `reassess_gate` →
recoleta → `assess_risk` de novo (nota "evidência faltando") — um ciclo de verdade no grafo, não
uma recursão de função. A trava: `revision_count` é incrementado a cada `RETURN`, e o roteador
força `finalize` quando esse contador passa do limite (`DCRA_REVISION_LIMIT`, padrão 2) — mesmo
que a UI já esconda a opção antes disso, o roteador é um segundo cinto de segurança
independente da UI.

### 8. `recursion_limit` — o limite duro contra loop infinito

Tanto `run()`/`resume()` (`build.py:74,102`, limite 40 supersteps do grafo inteiro) quanto o
agente investigador (`investigator.py:39`, limite 8 passos do loop ReAct) definem um teto rígido.
Sem isso, um bug de roteamento ou um agente "preso" rodaria para sempre — é o equivalente a um
`while True` sem `break`, mas com um alarme embutido pela própria biblioteca.

---

## Um grafo dentro do outro: o agente investigador

Como mencionado em `LANGCHAIN.md`, `create_agent` (usado em `investigator.py`) constrói, por
baixo, um **outro grafo LangGraph** — um loop fechado de "modelo decide tool → tool roda → modelo
lê resultado → decide de novo". Ou seja, este projeto tem dois níveis de LangGraph: o grafo
principal (determinístico, você desenhou cada aresta à mão) e, dentro de um nó dele
(`investigate`), um sub-agente cujo grafo interno foi montado automaticamente pela biblioteca. É
uma boa pergunta de entrevista para você mesmo responder: "onde termina o grafo que eu controlo e
começa o grafo que a biblioteca controla?" — resposta: no nó `investigate`, você entrega o
controle e só volta a ter certeza determinística quando o agente devolve sua lista de
`EvidenceItem`s.

---

## O que mais o LangGraph faz (além do que este projeto usa)

- **Subgrafos** (`checkpoint_ns` não-vazio) — grafos aninhados dentro de nós de um grafo maior,
  cada um com seu próprio namespace de checkpoint. Este projeto usa `checkpoint_ns=''` sempre —
  não há subgrafos explícitos (o agente investigador é uma exceção "invisível", não um subgrafo
  declarado por este código).
- **Streaming de eventos** — observar cada atualização de estado em tempo real
  (`.stream()`/`.astream()`) em vez de só `.invoke()` esperando o resultado final. O Streamlit
  deste projeto usa `.invoke()` síncrono (mais simples); uma versão com streaming mostraria a
  seção "Steps" preenchendo ao vivo, nó por nó.
- **`Send()`** — fan-out *dinâmico* (número de ramos decidido em tempo de execução, ex. "rode isso
  uma vez por item de uma lista de tamanho variável"). Este projeto usa fan-out **estático** (sempre
  exatamente 3 arestas) porque o número de leituras de evidência é fixo.
- **LangGraph Platform / Studio** — um produto separado (SaaS ou self-hosted) para visualizar e
  depurar grafos publicados interativamente, com um `langgraph.json` de configuração. Este projeto
  não está publicado nele — é rodado localmente via Streamlit. Vale conhecer de nome para
  entrevista: é para LangGraph o que um APM visual seria para uma aplicação distribuída.

## Como "navegar" o LangGraph neste projeto

- **Ver a topologia sem rodar nada**: `make graph` imprime o grafo compilado como Mermaid — compare
  com o diagrama já renderizado no `LEIAME.md`.
- **Ver o estado de um caso específico**: `get_state(compiled, thread_id)` (usado no botão "Reopen"
  do Streamlit, `src/dcra/graph/build.py:106`) devolve o `GraphState` completo tal como está
  gravado agora — é a forma programática do que `INFO_BANCO.md` mostra via SQL direto.
- **Ver a execução passo a passo, com tempo e ordem exata**: essa é a força do LangSmith — cada
  nó do grafo vira um "run" filho na árvore do trace, na ordem real de execução (incluindo os
  três `collect_*` lado a lado, provando visualmente o fan-out). Veja `LANGSMITH.md`.
