# LANGCHAIN — o que ele faz aqui, e o que mais ele faz

## A analogia rápida

Se você já usou o SDK cru de um provedor de LLM (`openai.chat.completions.create(...)`), sabe que
cada provedor tem seu próprio formato de mensagem, seu próprio jeito de pedir "tool calling", seu
próprio jeito de forçar saída em JSON. **LangChain é a camada de tradução** — um conjunto de
interfaces comuns (`ChatModel`, `Tool`, `Runnable`) que funcionam igual não importa se por trás
está OpenAI, Anthropic, Google, ou um modelo local. Pense nele como o **JDBC do mundo de LLMs**:
assim como JDBC deixa seu código Java falar com Postgres ou MySQL pela mesma interface, LangChain
deixa este projeto trocar de `gpt-4o` para `claude-opus-5` mudando uma variável de ambiente
(`LLM_PROVIDER`) em vez de reescrever código (veja ADR-019 em `DECISIONS.md` — foi literalmente o
que aconteceu neste projeto).

Este projeto usa **LangChain**, não os SDKs crus, em quatro pontos específicos. Cada um é um
conceito que aparece direto em entrevista.

---

## 1. O chat model provider-swappable — `build_chat_model`

**Onde**: `src/dcra/llm/factory.py:51`.

```python
from langchain_openai import ChatOpenAI
return ChatOpenAI(model=settings.llm_model, temperature=temperature, max_retries=2)
```

`ChatOpenAI` é a implementação da interface `BaseChatModel` do LangChain para a OpenAI. O código
que a *usa* (`interpret`, `draft_recommendation`) nunca importa nada de `langchain_openai`
diretamente — só recebe um objeto `model: Any` e chama métodos genéricos nele
(`.with_structured_output(...)`, `.invoke(...)`). Essa é a ideia central do LangChain: programar
contra a interface, não contra o provedor. O branch `anthropic` (comentado, `# pragma: no cover`)
no mesmo arquivo mostra o outro lado do contrato — trocar `ChatOpenAI` por `ChatAnthropic` sem
tocar em mais nada.

**O que aprender daqui**: em entrevista, isso é o argumento para "por que usar um framework em vez
de chamar a API direto" — não é só conveniência, é a diferença entre `if provider == "openai":
...` espalhado pelo código todo vs. **uma única fábrica** que isola a decisão.

## 2. Saída estruturada — `.with_structured_output(...)`

**Onde**: `interpret()` e `draft_recommendation()` em `src/dcra/llm/factory.py:70` e `:92`.

```python
parser = model.with_structured_output(StructuredChange)
result = parser.invoke(messages)   # já é um StructuredChange validado, não um texto
```

Sem isso, você pediria ao modelo para "responda em JSON", faria `json.loads()` na mão, e torceria
para o JSON ser válido e ter os campos certos. `.with_structured_output(PydanticModel)` empurra o
próprio *schema* do Pydantic para o provedor (via tool-calling nativo ou modo JSON garantido,
dependendo do modelo) — o retorno já vem validado contra `StructuredChange`/`Recommendation`
(`src/dcra/domain/models.py`). Se a validação falhar mesmo assim (o modelo alucinou um campo fora
do enum, por exemplo), o código tem um **retry com o erro embutido na próxima mensagem**
(`factory.py:76-83`) antes de desistir e levantar `InterpretationError` — uma estratégia de
"pedir de novo mostrando o erro" que você só ganha de graça por causa da validação declarativa.

**O que aprender daqui**: esse é o argumento contra "eu só faço parsing manual de JSON" — o padrão
schema-first (Pydantic → tool-calling → validação) é hoje o jeito profissional de extrair dados
estruturados de um LLM, porque a falha é *tipada e testável*, não um `KeyError` escondido em
produção.

## 3. Tools — `@tool` e `BaseTool`

**Onde**: `src/dcra/evidence/tools.py:100-118`.

```python
@tool
def get_asset_metadata(table: str, column: str | None = None) -> list[dict]:
    """Return catalog metadata for a table or table.column (data type, nullability, keys)."""
    return [...]
```

O decorador `@tool` do LangChain pega uma função Python comum e a envolve num objeto `BaseTool`
com **nome, descrição (a docstring!) e schema de parâmetros** — tudo derivado automaticamente das
type hints. É esse pacote (nome+descrição+schema) que o modelo recebe quando decide "devo chamar
`get_dependencies` com `table='orders', column='status'`?" — o LLM nunca vê o código Python, só a
assinatura declarada. Repare que a *mesma* função pura (`read_asset_metadata`,
`read_dependencies`, `read_downstream_usage`) é usada de duas formas: chamada diretamente pelos
nós do grafo (`nodes.py`, sem LLM no meio) e envolvida em `@tool` para o agente investigador poder
escolhê-la livremente. Isso é a diferença entre "função" e "tool": uma tool é uma função **mais**
metadados para um modelo decidir invocá-la.

## 4. Um agente ReAct limitado — `create_agent`

**Onde**: `src/dcra/agent/investigator.py:30-32`.

```python
from langchain.agents import create_agent
agent = create_agent(model, tools, system_prompt=_SYSTEM)
```

Isto é a peça mais "agêntica" do projeto — e a única em que o LLM decide, em tempo real, *quais*
tools chamar e em que ordem, dentro de um loop (pensar → chamar tool → ler resultado → repetir).
`create_agent` monta esse loop pronto (é o padrão **ReAct** — "Reasoning + Acting"): o modelo
recebe as 3 tools de evidência e decide sozinho quais usar para preencher a lacuna. O projeto
mantém isso **contido** de propósito (Constitution: nada de agentes irrestritos):
- `tools` é uma lista fixa das 3 leituras — o agente não pode inventar uma quarta ferramenta.
- `config={"recursion_limit": 8}` — trava dura contra um loop infinito.
- O `system_prompt` explicitamente diz "use ONLY the provided tools... When you have what the
  tools can give, stop."
- O agente **nunca decide risco nem rotas** — ele só devolve `EvidenceItem`s extras; quem decide o
  que fazer com eles é `assess_risk` (regras puras) de novo.

Nota histórica interessante (`DECISIONS.md`, ADR-021): esse mesmo agente antes usava
`langgraph.prebuilt.create_react_agent`. Foi trocado porque o LangGraph deprecou essa função e
recomendou migrar para `langchain.agents.create_agent` — ou seja, **por baixo dos panos,
`create_agent` também constrói um grafo LangGraph** (você está usando LangGraph duas vezes neste
projeto: uma vez explicitamente para o workflow inteiro, outra vez implicitamente, escondida
dentro desse agente). Vale entender essa sobreposição — é uma pergunta comum: "qual a diferença
entre um agente LangChain e um grafo LangGraph?" Resposta curta: hoje, um agente *é* um grafo
LangGraph pré-montado com um padrão específico (loop de tool-calling); LangGraph é a ferramenta
mais geral por baixo.

## 5. Bônus: um cliente MCP embrulhado como tools do LangChain

**Onde**: `src/dcra/mcp/client.py:59`, pacote `langchain-mcp-adapters`.

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
client = MultiServerMCPClient(_SERVER)
tools = await client.get_tools()   # tools remotas do servidor MCP, já como BaseTool do LangChain
```

Isso mostra outra faceta do LangChain: ele não só define `@tool` para funções locais, como
consegue **importar tools de um servidor MCP remoto e apresentá-las com a mesma interface
`BaseTool`**. Do ponto de vista de quem consome, uma tool MCP e uma tool `@tool` local são
indistinguíveis — é o mesmo motivo pelo qual o modo `DCRA_USAGE_VIA_MCP=1` não muda nenhum outro
código do grafo (veja `GUIA_DE_USO.md` §6 e `docs/mcp.md`).

---

## O que mais o LangChain faz (além do que este projeto usa)

Este projeto usa uma fatia deliberadamente pequena. Para entrevista, vale saber que o ecossistema
completo inclui:

- **LCEL (LangChain Expression Language)** — compor `Runnable`s com `|` (pipe), tipo
  `prompt | model | parser`. Este projeto não usa (prefere chamadas diretas + LangGraph para o
  controle de fluxo), mas é o "modo chain" mais comum em tutoriais.
- **Memory / histórico de conversa** — gerenciar múltiplos turnos de chat. Aqui não existe
  "conversa" — cada caso é uma execução única do grafo.
- **Retrievers / RAG** — buscar documentos relevantes (embeddings + vector store) para dar
  contexto ao modelo. Deliberadamente fora de escopo aqui (README, "What was deliberately not
  built") — a "evidência" vem de tools estruturadas, não de busca semântica em texto.
- **Document loaders** — ingerir PDFs, páginas web, etc. Não usado (não há documentos no domínio).
- **Callbacks / tracing** — o mecanismo por trás do LangSmith (próximo documento,
  `LANGSMITH.md`) — funciona por instrumentação automática, sem precisar chamar nada explicitamente.
- **Centenas de integrações de tools prontas** (busca web, código, bancos de dados, APIs de
  terceiros) — este projeto só usa tools caseiras, porque o domínio é fechado e simulado de
  propósito.

## Como "navegar" o LangChain

Diferente do LangGraph (que tem uma representação visual, o grafo) e do LangSmith (que tem uma UI
web), o LangChain em si é **uma biblioteca**, não um produto com interface própria. As formas de
"explorar" o que ele está fazendo:

- **Inspecionar o schema de uma tool** — abra um shell Python (`uv run python`) e rode:
  ```python
  from dcra.evidence.tools import make_evidence_tools
  from dcra.evidence.dataset import default_dataset
  tools = make_evidence_tools(default_dataset())
  print(tools[0].name, tools[0].args_schema.model_json_schema())
  ```
  Isso mostra exatamente o que o modelo recebe quando decide chamar essa tool.
- **A documentação oficial** — python.langchain.com — é onde ver o catálogo completo de
  integrações (chat models, tools, vector stores) além do que este projeto usa.
- **O rastro de execução** — na prática, a forma mais rica de "ver o LangChain funcionando" neste
  projeto é o LangSmith (próximo arquivo) — cada chamada `.invoke()` de um chat model ou de uma
  tool vira um "run" visível na árvore do trace.
