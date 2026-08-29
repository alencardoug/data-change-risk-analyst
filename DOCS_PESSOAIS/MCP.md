# MCP — Model Context Protocol, o incremento V1 deste projeto

Não foi pedido diretamente, mas é um arquivo que vale a pena existir: **MCP** aparece cada vez
mais em vagas de AI Engineering, e este projeto tem um incremento real e pequeno dele (ADR-020)
que é uma ótima resposta pronta para "você já usou MCP?".

## A analogia rápida

Uma função Python comum é como pedir um favor a um colega **na mesma sala**: você grita o pedido,
ele responde na hora, vocês compartilham a mesma mesa (o mesmo processo). Uma **tool MCP** é pedir
o mesmo favor a alguém **em outro prédio, por telefone, com um protocolo formal de "alô, aqui está
o que eu sei fazer, me manda o pedido no formato certo"**. MCP é esse protocolo de telefone — um
padrão aberto (da Anthropic) para que qualquer cliente (um agente, uma IDE, um app de chat) descubra
e chame capacidades expostas por qualquer servidor, sem os dois lados precisarem se conhecer de
antemão além de falar o mesmo protocolo.

## O que existe neste projeto

Antes do incremento V1, as três leituras de evidência (`get_asset_metadata`, `get_dependencies`,
`get_downstream_usage`) eram só funções Python locais, embrulhadas como tools do LangChain
(`LANGCHAIN.md`). O incremento move **uma única delas** — `get_downstream_usage` — para rodar
atrás de um servidor MCP local, ligado por uma variável de ambiente
(`DCRA_USAGE_VIA_MCP=1`, veja `GUIA_DE_USO.md` §6). É deliberadamente a menor mudança possível
que ainda demonstra a fronteira cliente/servidor de verdade — as outras duas tools continuam
locais, então o "antes/depois" cabe num diff só e numa linha do `step_log`.

### O servidor — `src/dcra/mcp/server.py`

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("dcra-evidence")

@mcp.tool()
def get_downstream_usage(table: str, column: str) -> list[dict]:
    ...

mcp.run(transport="stdio")
```

`FastMCP` é a forma "de alto nível" de declarar um servidor MCP — parecido com `@tool` do
LangChain, mas para o outro lado do protocolo: `@mcp.tool()` expõe a função com um schema
descoberto automaticamente, para qualquer cliente MCP puxar via `list-tools`. O transporte aqui é
**stdio** (entrada/saída padrão) — o cliente sobe o servidor como um **subprocesso** e conversa
com ele por pipes, não por rede HTTP. Rode `python -m dcra.mcp.server` sozinho para ver o servidor
de pé, esperando conexão.

### O cliente — `src/dcra/mcp/client.py`

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
client = MultiServerMCPClient({"dcra-evidence": {"command": ..., "args": [...], "transport": "stdio"}})
tools = await client.get_tools()
tool = next(t for t in tools if t.name == "get_downstream_usage")
result = await tool.ainvoke({"table": table, "column": column})
```

`langchain_mcp_adapters` faz a ponte: conecta num (ou mais) servidores MCP, descobre as tools
deles, e as devolve **já como objetos `BaseTool` do LangChain** — o mesmo tipo que `@tool` produz
localmente. É por isso que trocar de "leitor local" para "leitor via MCP" não muda nada no resto
do grafo (`GraphDeps.usage_reader`, `src/dcra/graph/deps.py:36`): dos dois lados, o que chega é
uma lista de `EvidenceItem`, só que um caminho passou por um processo separado e um protocolo de
rede (mesmo que local) no meio.

### O ciclo de vida de uma chamada MCP

1. **Spawn** — o cliente sobe `python -m dcra.mcp.server` como subprocesso (a cada leitura, neste
   projeto — não há um servidor de longa duração rodando à parte).
2. **Initialize** — handshake inicial do protocolo.
3. **List-tools** — o cliente pergunta "o que você sabe fazer?", recebe o schema de
   `get_downstream_usage`.
4. **Call** — o cliente invoca a tool com os argumentos, espera o resultado (JSON-RPC sobre stdio).
5. **Shutdown** — o subprocesso termina.

### Falha graciosa — o ponto mais importante para defender em entrevista

```python
def read_downstream_usage_via_mcp(table: str, column: str) -> list[EvidenceItem]:
    try:
        return asyncio.run(_fetch(table, column))
    except Exception:
        return _unavailable(table, column)
```

Se o servidor MCP não sobe, trava, ou responde algo inesperado — **qualquer exceção** vira um
único `EvidenceItem` com `status=UNAVAILABLE`, exatamente como uma fonte de evidência desabilitada
(`FR-024`, veja `REGRAS.md` — o fator `EVIDENCE_UNAVAILABLE` sobe o risco, a confiança da
recomendação cai para `REDUCED`). O grafo **nunca quebra** por causa de um servidor MCP fora do
ar — ele degrada, chega ao portão humano do mesmo jeito, e um teste garante esse comportamento
(`tests/mcp/test_mcp_usage_tool.py`).

## Três formas de "chamar uma função" — a tabela que vale decorar

| | Função local | Tool do LangChain (`@tool`) | Tool MCP |
|---|---|---|---|
| Quem chama | seu próprio código | um modelo (LLM), via tool-calling | um cliente MCP qualquer — modelo, IDE, outro agente |
| Onde roda | mesmo processo | mesmo processo (é uma função Python embrulhada) | processo separado (subprocesso local ou servidor remoto) |
| Como é descoberta | você importa e chama direto | o LLM recebe nome+descrição+schema no prompt/tool-calling da API | o cliente pergunta em tempo de execução via `list-tools` |
| Acoplamento | total (mesmo código-fonte) | ainda total (mesmo processo, mesmo deploy) | nenhum — cliente e servidor só precisam falar o protocolo |
| Neste projeto | `read_asset_metadata`, `read_dependencies` chamados direto pelos nós | as mesmas funções embrulhadas em `@tool` para o agente investigador | `get_downstream_usage` quando `DCRA_USAGE_VIA_MCP=1` |

## O que MCP adiciona aqui — e o que ele não adiciona

- **Adiciona**: uma fronteira de interoperabilidade real — qualquer cliente MCP (não só este
  projeto) poderia consumir `get_downstream_usage` sem saber Python nem importar nada deste
  repositório.
- **Não adiciona**: orquestração. MCP não é um motor de workflow — quem ainda decide o quê fazer,
  quando pausar, e como rotear é o LangGraph. MCP só mudou **onde** uma tool roda e **como** ela é
  alcançada; não substitui LangChain, LangGraph, o banco, nem vira uma "segunda camada de
  orquestração" por cima da primeira.

## Perguntas de entrevista que este incremento responde

- **"Por que só uma tool via MCP?"** — a menor mudança que já demonstra a fronteira
  cliente/servidor/transporte, sem inflar a complexidade operacional do V0 nem exigir infra extra.
- **"O que acontece se o servidor MCP cair?"** — degrada para `UNAVAILABLE`, nunca derruba o app;
  o mesmo caminho de "confiança reduzida" já existia para qualquer fonte de evidência desabilitada.
- **"Diferença entre tool local, tool LangChain e tool MCP?"** — veja a tabela acima; é
  essencialmente uma escala de acoplamento crescente, da chamada de função até um protocolo de
  rede.
- **"MCP substitui LangChain/LangGraph?"** — não; são camadas ortogonais. MCP resolve
  "como uma capacidade é exposta e descoberta"; LangGraph resolve "em que ordem e sob que
  condições as coisas acontecem"; LangChain resolve "como falar com o modelo e empacotar tools de
  forma uniforme" — os três coexistem neste projeto ao mesmo tempo.

## Como explorar

Veja `GUIA_DE_USO.md` §6 para rodar o app com `DCRA_USAGE_VIA_MCP=1` e comparar o `step_log`
resultante com o modo local — devem ser idênticos em conteúdo, diferindo só na linha
`collect_usage (via MCP): N item(s)`.
