# INDICE — mapa de leitura desta pasta

`DOCS_PESSOAIS/` é a sua versão pessoal, em português e mais explicada, dos documentos técnicos
do projeto (que continuam em inglês na raiz e em `docs/`, `specs/`). Nada aqui substitui a fonte
da verdade em código — cada arquivo aponta para o `arquivo.py:linha` exato de onde tirou cada
afirmação.

## Ordem de leitura sugerida

1. **`LEIAME.md`** — visão geral do projeto (tradução do `README.md`): o que é, o diagrama do
   fluxo, as três decisões de arquitetura, o que foi deliberadamente não construído.
2. **`REGRAS.md`** — a política de risco LOW/MEDIUM/HIGH, regra por regra, com o porquê de cada
   uma. Leia antes da demo para entender *por que* cada caso classificou como classificou.
3. **`DEMO.md`** — o roteiro de 2–3 minutos e os 8 cenários (S1–S8) que provam cada caminho do
   grafo. Faça isso rodando de verdade, com o app aberto.
4. **`GUIA_DE_USO.md`** — depois da demo guiada, o catálogo livre: um exemplo de entrada para cada
   fator de risco, como testar o loop de revisão, o modo MCP, resume após restart, os testes
   automatizados.
5. **`INFO_BANCO.md`** — o que ficou gravado no Postgres depois de tudo isso: as 5 tabelas
   (1 de negócio + 4 de infraestrutura do LangGraph), com dados reais tirados do seu próprio banco.
6. **`LANGCHAIN.md`**, **`LANGGRAPH.md`**, **`LANGSMITH.md`**, **`MCP.md`** — os quatro pilares de
   ferramenta, cada um explicando: o que é, onde é usado neste projeto (com referências de
   código), o que mais a ferramenta faz além do que este projeto usa, e como navegar sua
   interface/produto (quando existir uma).

## Qual pergunta cada arquivo responde

| Pergunta | Arquivo |
|---|---|
| "O que este projeto faz, em uma página?" | `LEIAME.md` |
| "Por que este caso deu MEDIUM e não LOW?" | `REGRAS.md` |
| "Como eu provo que o projeto funciona, rápido?" | `DEMO.md` |
| "Que outras entradas eu testo para ver X ou Y comportamento?" | `GUIA_DE_USO.md` |
| "O que exatamente está gravado no banco?" | `INFO_BANCO.md` |
| "Como o LangChain é usado aqui, e o que mais ele faz?" | `LANGCHAIN.md` |
| "Como o LangGraph é usado aqui, e o que mais ele faz?" | `LANGGRAPH.md` |
| "Como eu vejo um trace de uma execução, e o que mais o LangSmith faz?" | `LANGSMITH.md` |
| "O que é esse tal de MCP, e por que tem um servidor aqui?" | `MCP.md` |

## Glossário rápido (os termos que se repetem em todos os arquivos)

- **`thread_id`** — o identificador de um caso. É o mesmo valor em três lugares: `ChangeRequest.id`
  / `analysis_record.id` (Postgres) e o `thread_id` das tabelas de checkpoint do LangGraph e dos
  metadados de um trace no LangSmith. A "chave universal" para reconstruir a história de um caso.
- **Checkpoint** — uma "foto" congelada do estado do grafo depois de um passo, salva no Postgres.
  É o que permite `interrupt()`/`resume()` sobreviver a um restart. Ver `INFO_BANCO.md` §2 e
  `LANGGRAPH.md` §6.
- **Reducer** — a função que decide como mesclar duas escritas concorrentes no mesmo campo de
  estado (ex. `merge_evidence`). Ver `LANGGRAPH.md` §2.
- **Fan-out / fan-in** — vários nós rodando em paralelo a partir de um nó comum (fan-out), e o
  grafo esperando todos terminarem antes do próximo nó (fan-in). Ver `LANGGRAPH.md` §3.
- **`interrupt()` / `Command(resume=...)`** — a pausa real do grafo, esperando uma decisão
  externa (o portão de revisão humana). Ver `LANGGRAPH.md` §5.
- **Saída estruturada (`structured output`)** — pedir ao LLM uma resposta que já vem validada
  contra um schema Pydantic, em vez de texto livre. Ver `LANGCHAIN.md` §2.
- **Tool** — uma função com nome/descrição/schema que um modelo pode decidir chamar. Pode ser
  local (`@tool`) ou remota (MCP). Ver `LANGCHAIN.md` §3 e `MCP.md`.
- **Agente ReAct** — um loop onde o modelo decide, passo a passo, quais tools chamar até ter
  informação suficiente. Aqui, limitado a 3 tools e 8 passos. Ver `LANGCHAIN.md` §4.
- **Fator de risco (`RiskFactor`)** — um predicado nomeado que, se disparar, contribui para a
  categoria de risco final (ex. `IN_PRIMARY_KEY`, `REFERENCED_BY_VIEW`). Ver `REGRAS.md`.
- **ADR** (Architecture Decision Record) — um registro formal de uma decisão de arquitetura, com
  contexto, alternativas consideradas e consequências. Vivem em `DECISIONS.md` na raiz; os
  arquivos desta pasta citam os números relevantes (ex. ADR-019, ADR-020, ADR-021) sem repetir o
  texto completo.

## O que NÃO está aqui

Esta pasta é sobre **entender e explorar** o que já existe. Ela não é o lugar para registrar novas
decisões de arquitetura (isso vai em `DECISIONS.md`), nem para abrir uma nova feature via SDD
(isso segue o fluxo descrito em `AGENTS.md`/`SDD_WORKFLOW.md`). Se algo aqui ficar desatualizado
depois de uma mudança real no código, é sinal de atualizar o arquivo específico — não de duplicar
a explicação em outro lugar.
