# LANGSMITH — o que ele faz aqui, e o que mais ele faz

## A analogia rápida

Se o seu app fosse um restaurante, o LangChain seria a cozinha (onde a comida é de fato preparada)
e o LangGraph seria o fluxo de pedidos entre as estações (a comanda passando de quem corta, para
quem grelha, para quem monta o prato, com uma pausa se faltar um ingrediente). **LangSmith é a
câmera de vídeo em cada estação, gravando tudo** — quanto tempo cada prato ficou em cada estação,
o que exatamente entrou e saiu de cada uma, e quanto custou o ingrediente usado. Você não precisa
instalar câmera nenhuma na cozinha (nenhum código muda) — LangChain e LangGraph já vêm com o
suporte para serem filmados, você só liga a câmera com três variáveis de ambiente.

## Como está ligado neste projeto

Puramente por variáveis de ambiente — **nenhuma linha de código chama o LangSmith diretamente**.
Isso é possível porque LangChain/LangGraph têm instrumentação automática embutida: toda vez que
você chama `.invoke()` num chat model, numa tool, ou no grafo compilado, a biblioteca decide
sozinha (olhando essas variáveis) se deve mandar os dados de execução para o LangSmith.

```bash
# .env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=dcra
```

`Settings.from_env()` (`src/dcra/config.py:31`) só lê `LANGSMITH_TRACING` para decidir um booleano
interno — nem isso é usado para acionar nada explicitamente; é a própria variável de ambiente
`LANGSMITH_TRACING` (lida diretamente pelas bibliotecas, não pelo `Settings` deste projeto) que
liga a instrumentação global do processo. Rode qualquer caso (Streamlit ou os testes
`llm_integration`) com essas três variáveis definidas e ele já aparece rastreado.

## Como navegar a interface (smith.langchain.com)

1. Entre em <https://smith.langchain.com> com a conta que você criou.
2. No menu à esquerda, ache **Projects** (ou "Tracing Projects") e abra o projeto **`dcra`** — o
   nome vem exatamente de `LANGSMITH_PROJECT=dcra`.
3. Cada linha na lista é um **"root run"** — uma chamada de nível mais alto. Cada
   `compiled.invoke(...)` (uma chamada a `run()` ou a `resume()` em `src/dcra/graph/build.py`) gera
   um root run novo. Ou seja: **um caso que passa pelo portão de revisão gera pelo menos dois
   root runs** — um para a execução até a pausa, outro para a retomada depois da decisão humana.
4. Clique num root run para abrir a **árvore de execução** — é aqui que a mágica acontece: você vê
   cada nó do grafo como um run filho, na ordem real em que rodou.

### O que procurar dentro da árvore (do `docs/observability.md` original do projeto, testado de
verdade contra uma execução real)

| No trace | O que isso te mostra |
|---|---|
| A árvore de runs-filhos sob o root | a ordem de execução dos nós — `interpret`, depois os três `collect_*` **como irmãos, lado a lado** (a prova visual do fan-out paralelo descrito em `LANGGRAPH.md`), depois `assess_risk` só depois que os três terminam, depois o caminho condicional escolhido |
| O input/output do run `interpret` | o texto cru que entrou, e o `StructuredChange` que saiu — uma chamada de saída estruturada, não texto livre (veja `LANGCHAIN.md`) |
| Um "buraco" na árvore terminando em `human_review` | o `interrupt()` — a execução parou ali; o próximo root run relacionado (mesmo `thread_id` nos metadados) é o `resume` |
| `investigate` → runs de agente aninhados | o loop ReAct do agente investigador: cada chamada a `get_asset_metadata`/`get_dependencies`/`get_downstream_usage`, e os "turnos" do modelo entre elas. Confirme que ele só chama essas três tools e para dentro do limite de recursão (8) |
| Tokens + latência em cada run de modelo | o custo real de interpretar vs. recomendar vs. o loop do agente — útil pra responder "onde está o gargalo/custo" numa entrevista |
| `assess_risk` e os nós de roteamento | **nenhuma chamada de modelo** — são funções puras. Se algum dia você vir uma chamada de LLM aparecer aqui, é sinal de que alguém quebrou a fronteira determinístico/probabilístico (Constitution IV) |

### Achando o trace de um caso específico

O jeito mais confiável é abrir o caso no app **enquanto olha o LangSmith** — o root run mais novo
na lista do projeto, criado no momento em que você clicou "Analyze", é o seu. Para casos passados,
o `thread_id` (visível em `INFO_BANCO.md` como o `id` de `analysis_record`) aparece nos metadados
de configuração do run (`configurable.thread_id`) — dá para inspecionar isso abrindo o run e
olhando o painel de metadata/input, já que é o mesmo valor passado em
`config={"configurable": {"thread_id": ...}}` em `build.py`.

### Comparando com o registro no banco

O campo `step_log` de `analysis_record` (veja `INFO_BANCO.md`) é a versão "texto simples, sem
UI" do mesmo relato que o trace mostra visualmente:

```
interpret: DROP_COLUMN on orders
collect_asset: 1 item(s)
collect_deps: 2 item(s)
collect_usage: 1 item(s)
assess_risk: pass 1 → MEDIUM (REFERENCED_BY_VIEW, ACTIVELY_READ)
recommend: v1 PROCEED_WITH_MITIGATION (NORMAL)
human_review: APPROVE
finalize: APPROVED
```

`thread_id` é a chave que junta as três vistas do mesmo caso: o registro no Postgres, os
checkpoints passo-a-passo, e o trace no LangSmith.

## O que mais o LangSmith faz (além de tracing passivo)

Este projeto só usa a fatia "observar automaticamente". O produto completo também oferece:

- **Datasets & Evaluations** — gravar um conjunto de casos de teste com resultado esperado, e
  rodar avaliações automáticas (inclusive usando outro LLM como "juiz") toda vez que você mudar um
  prompt ou trocar de modelo, para detectar regressão. Fora de escopo aqui (o projeto usa testes
  determinísticos com modelo falso para isso, veja `GUIA_DE_USO.md` §7), mas é o "próximo passo
  natural" que qualquer entrevistador vai perguntar: "como vocês garantem que uma mudança no
  prompt não piorou a qualidade?"
- **Prompt Hub** — versionar e compartilhar prompts como artefatos próprios, fora do código. Este
  projeto mantém os prompts como strings Python simples (`_INTERPRET_SYS`, `_RECOMMEND_SYS` em
  `llm/factory.py`) — suficiente para o escopo, mas um time maior costuma "promover" prompts
  estáveis para o Hub.
- **Monitoring/Alerting em produção** — dashboards de latência, taxa de erro e custo agregado ao
  longo do tempo, com alertas. Faz sentido numa aplicação com tráfego real; este projeto é uma
  demo local, então essa camada nunca chega a ser exercitada.
- **Anotação humana de runs** — marcar um trace como "bom"/"ruim" direto na interface, útil para
  construir datasets de avaliação a partir de tráfego real observado.

## Por que isso importa em entrevista

A pergunta mais comum sobre sistemas agênticos em produção não é "seu agente funciona?" — é
"quando ele não funciona, como você descobre por quê, sem re-rodar tudo adivinhando?". A resposta
aqui é dupla e vale a pena ter pronta: **auditoria estruturada** (o `step_log` gravado em todo
`analysis_record`, sempre disponível, sem depender de nenhum serviço externo) **e observabilidade
visual sob demanda** (o trace do LangSmith, rico em latência/tokens/árvore de chamadas, ligado só
quando você precisa investigar fundo). Nenhuma delas sozinha seria suficiente: só o log de texto
não mostra paralelismo nem custo; só o LangSmith não sobrevive independente de uma conta externa
estar disponível. As duas juntas, com o mesmo `thread_id` como chave, são o padrão real de
observabilidade de um sistema agêntico.
