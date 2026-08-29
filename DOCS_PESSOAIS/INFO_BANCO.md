# INFO_BANCO — o banco de dados deste projeto

Este documento explica, com dados reais tirados do seu Postgres local (via `docker exec ... psql`,
em 2026-08-28), tudo que existe dentro do banco `dcra`. Não é uma cópia do `data-model.md` — é uma
leitura literal do banco como ele está agora, coluna a coluna, com exemplos verdadeiros.

## Visão geral: um banco, duas "gavetas"

O Postgres deste projeto guarda **dois tipos de coisa completamente diferentes**, que só por
coincidência moram no mesmo banco:

1. **`analysis_record`** — a tabela de negócio. Uma linha por caso analisado (a "prateleira de
   arquivos" do analista de risco). Esta é a tabela que você, como usuário do produto, quer olhar.
2. **`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`, `checkpoint_migrations`** — infraestrutura
   interna do **LangGraph**. É a "memória de curto prazo" do motor de workflow: o estado exato do
   grafo, congelado a cada passo, para que um `interrupt()` (a pausa de revisão humana) sobreviva a
   um restart do app ou do banco. Você nunca escreve nessas tabelas diretamente — o pacote
   `langgraph-checkpoint-postgres` (classe `PostgresSaver`) cria e gerencia esse schema sozinho,
   via `saver.setup()` (`src/dcra/persistence/checkpointer.py:24`).

Analogia: pense em `analysis_record` como a pasta final arquivada de um processo já decidido, e nas
tabelas `checkpoint_*` como o "controle de versão" (tipo um `git log` binário) de cada passo que o
processo deu enquanto ainda estava em andamento — inclusive os passos que aconteceram *antes* dele
ficar pronto.

Quem cria essas 5 tabelas, e quando:
- `analysis_record`: `PostgresRepository.setup()` roda o SQL de `src/dcra/persistence/schema.sql`
  (um `CREATE TABLE IF NOT EXISTS`).
- As 4 tabelas `checkpoint*`: `PostgresSaver.setup()`, chamado dentro de
  `open_checkpointer`/`make_checkpointer` (`src/dcra/persistence/checkpointer.py`). É código de
  terceiros (LangGraph), não deste projeto — por isso não há um `.sql` para elas no repositório.

Estado agora (contagens reais, 2026-08-28):

| Tabela | Linhas | Dono do schema |
|---|---:|---|
| `analysis_record` | 13 | este projeto (`schema.sql`) |
| `checkpoints` | 115 | LangGraph (`PostgresSaver`) |
| `checkpoint_writes` | 544 | LangGraph |
| `checkpoint_blobs` | 201 | LangGraph |
| `checkpoint_migrations` | 10 | LangGraph |

---

## 1. `analysis_record` — a tabela de negócio

Fonte da verdade: `src/dcra/persistence/schema.sql` + o modelo Pydantic `AnalysisRecord` em
`src/dcra/domain/models.py:132`. **Uma linha = um caso analisado, do início ao fim** (FR-017 da
spec: "one traceable record per analysed change").

### Colunas

| Coluna | Tipo Postgres | Nulo? | Para que serve |
|---|---|---|---|
| `id` | `TEXT` (PK) | não | O identificador do caso. É o **mesmo valor** que `ChangeRequest.id` (um UUID) e que o `thread_id` usado nas tabelas de checkpoint — é a chave que junta as duas "gavetas" do banco (veja §3). |
| `change_request` | `JSONB` | não | O pedido original, congelado: texto cru (`raw_text`), quem pediu (`submitted_by`), quando (`submitted_at`). É o "ticket de entrada". |
| `structured_change` | `JSONB` | sim | O pedido depois de interpretado pelo LLM: `operation` (DROP_COLUMN/ALTER_COLUMN/ADD_INDEX), `target_table`, `target_column`, etc. `NULL` quando o caso nunca passou pelo nó `interpret` do grafo real (ver nota sobre dados sintéticos abaixo). |
| `evidence` | `JSONB` | não (default `[]`) | Lista de `EvidenceItem` — tudo que os 3 leitores (asset/deps/usage) e, se necessário, o agente investigador, coletaram. Cada item tem `kind`, `key`, `status` (OBTAINED/UNAVAILABLE), `source`, `payload`. |
| `risk_assessments` | `JSONB` | não (default `[]`) | **Histórico completo** de avaliações de risco — uma por "passada" (`pass_number`). Normalmente 1 item; sobe para 2+ quando o revisor devolve o caso marcando "evidência faltando" (o caso é reavaliado). |
| `recommendations` | `JSONB` | não (default `[]`) | Histórico de recomendações da IA — uma por versão (`version`). Sobe quando o revisor pede revisão (`RETURN`). |
| `review_actions` | `JSONB` | não (default `[]`) | Histórico de decisões humanas: `APPROVE`/`REJECT`/`RETURN`, quem decidiu, nota opcional. Vazio quando o caso nunca chegou ao portão de revisão humana (risco LOW). |
| `reviewed` | `BOOLEAN` | não | `true` se algum humano decidiu algo; `false` se o caso foi **auto-finalizado** (LOW, sem revisão). |
| `outcome` | `TEXT` | não | `APPROVED` \| `REJECTED` \| `AUTO_FINALIZED` — o veredito final. |
| `final_recommendation_version` | `INTEGER` | não | Número da última versão de recomendação usada no veredito. |
| `step_log` | `JSONB` | não (default `[]`) | O "diário de bordo" do caso — uma linha de texto por passo do grafo, em ordem (ex.: `"assess_risk: pass 1 → MEDIUM (...)"`). É o mesmo conteúdo que aparece na aba "Steps" do Streamlit e é o companheiro textual de um trace do LangSmith (veja `LANGSMITH.md`). |
| `created_at` | `TIMESTAMPTZ` | não (default `now()`) | Quando a linha foi criada. |
| `finalized_at` | `TIMESTAMPTZ` | não (default `now()`) | Quando o caso foi (re)finalizado — atualizado a cada `UPSERT` (ex.: se o caso for reaberto e re-finalizado). |

Não há colunas separadas para "risco atual" ou "recomendação atual" — de propósito. Tudo o que
varia por caso é um **array JSON append-only**; o "estado atual" é sempre `arr[-1]`. Isso é
literalmente o mesmo padrão de reducer que o LangGraph usa em memória (`append_list` em
`src/dcra/graph/state.py`) — a tabela persiste o histórico completo, não um snapshot mutável.

### Relacionamentos

Não há chaves estrangeiras declaradas no Postgres. O relacionamento é **lógico**, via o valor de
`id`:

```
analysis_record.id  ≡  ChangeRequest.id  ≡  thread_id nas tabelas checkpoint_*  ≡  thread_id de um trace no LangSmith
```

Essa é a "chave universal" do projeto — com ela você consegue reconstruir a história completa de
um caso em três lugares diferentes (registro final no Postgres, replay passo-a-passo nos
checkpoints, trace visual no LangSmith).

### Contagem e perfil das linhas (real, agora)

**13 linhas.** Distribuição por `outcome`:

| `outcome` | Linhas |
|---|---:|
| `AUTO_FINALIZED` | 12 |
| `APPROVED` | 1 |
| `REJECTED` | 0 |

Duas origens diferentes de dados, e vale a pena distingui-las para não se confundir ao explorar:

- **10 linhas são fixtures sintéticas mínimas** (`raw_text = "drop column orders.notes_internal"`,
  `step_log = ["a", "b"]`, `evidence = []`, `structured_change = NULL`). Vêm dos testes de
  round-trip do repositório (`tests/unit/test_repository.py`, tarefa T068) — eles gravam um
  `AnalysisRecord` mínimo só para provar que "salvar → ler de volta" preserva os dados
  byte-a-byte. Não passaram pelo grafo de verdade.
- **3 linhas são execuções reais do grafo completo contra `gpt-4o` + Postgres real** — a tarefa
  **T061** ("rodar S1–S8 contra modelo real uma vez"). São essas que valem a pena estudar.

### Top 3 exemplos reais (linhas de verdade, não fixtures)

**1) Um DROP_COLUMN de risco MEDIUM, aprovado por um humano** —
`id = t061-f1d28e6d-f0b0-4f3c-ad81-5412cfcbb814`

```json
{
  "change_request": {"raw_text": "Remove the column customer_legacy_id from the orders table", "submitted_by": "tester"},
  "structured_change": {"operation": "DROP_COLUMN", "target_table": "orders", "target_column": "customer_legacy_id", "confidence": 0.95},
  "risk_assessments[-1]": {"category": "MEDIUM", "factors": [
      {"code": "REFERENCED_BY_VIEW", "severity": "MEDIUM", "description": "Referenced by 2 view/materialization(s)."},
      {"code": "ACTIVELY_READ", "severity": "MEDIUM", "description": "1 downstream consumer(s) still read this column."}
  ]},
  "recommendations[-1]": {"disposition": "PROCEED_WITH_MITIGATION", "confidence": "NORMAL",
      "rationale": "The column 'customer_legacy_id' ... is referenced by two views ... and is actively read by a downstream service ('cs_lookup')...",
      "mitigations": ["Update or refactor the views...", "Coordinate with the 'cs_lookup' service team...", "Conduct a thorough impact analysis..."]},
  "review_actions[-1]": {"decision": "APPROVE", "reviewer": "data.owner"},
  "outcome": "APPROVED", "reviewed": true,
  "step_log": [
    "interpret: DROP_COLUMN on orders", "collect_asset: 1 item(s)", "collect_deps: 2 item(s)",
    "collect_usage: 1 item(s)", "assess_risk: pass 1 → MEDIUM (REFERENCED_BY_VIEW, ACTIVELY_READ)",
    "recommend: v1 PROCEED_WITH_MITIGATION (NORMAL)", "human_review: APPROVE", "finalize: APPROVED"
  ]
}
```

Este é o caso "canônico" do README/LEIAME — o cenário S2 do `quickstart.md`, rodado de verdade.

**2) Um ADD_INDEX de risco LOW, auto-finalizado (sem revisão humana)** —
`id = t061-ed6d565e-b7e6-44dd-b975-2b46cd08b833`, `raw_text = "add index on orders(customer_id)"`,
`outcome = AUTO_FINALIZED`, `reviewed = false`. Mostra o caminho "feliz e rápido": risco LOW nunca
chega ao portão humano (regra `route_after_recommend` em `src/dcra/graph/nodes.py:202`).

**3) Uma fixture de teste do repositório** —
`id = c9743680-566a-4a3e-81d9-41be9c902c49`, `raw_text = "drop column orders.notes_internal"`,
`structured_change = NULL`, `evidence = []`, `step_log = ["a", "b"]`, `outcome = AUTO_FINALIZED`.
Serve para ilustrar o "outro tipo" de linha na tabela — dado de teste, não uma decisão real.

---

## 2. As 4 tabelas de checkpoint do LangGraph

Estas tabelas são a implementação de **persistência de estado** do `PostgresSaver`. Pense nelas
como o Postgres fazendo o papel que, em outro contexto, o Git faz para código: cada "commit" é o
estado do grafo depois de um nó rodar. Isso é o que torna `interrupt()`/`resume()` (a pausa para
revisão humana) sobreviver a um restart — veja `LANGGRAPH.md` para a mecânica completa.

### `checkpoints` — um "commit" de estado por passo

| Coluna | Tipo | Para que serve |
|---|---|---|
| `thread_id` | `TEXT` | O caso (mesmo valor de `analysis_record.id`). |
| `checkpoint_ns` | `TEXT` | "Namespace" do checkpoint — vazio (`''`) no nosso grafo, que não usa subgrafos. |
| `checkpoint_id` | `TEXT` (parte da PK) | Um UUID ordenável no tempo (UUIDv7-like) identificando este passo exato. |
| `parent_checkpoint_id` | `TEXT` | O checkpoint anterior — forma uma **lista encadeada**, o "histórico de commits" de um caso. |
| `type` | `TEXT` | Formato de serialização (tipicamente vazio/`msgpack`, controlado pelo `JsonPlusSerializer`). |
| `checkpoint` | `JSONB` | O envelope do checkpoint (metadados de versão de canal — os *valores* grandes ficam em `checkpoint_blobs`, não aqui). |
| `metadata` | `JSONB` | De onde veio esse passo: `{"step": -1, "source": "input", "parents": {}}` no primeiro checkpoint de um thread, incrementando a cada superstep. |

PK composta: `(thread_id, checkpoint_ns, checkpoint_id)`. Índice extra em `thread_id` (é assim que
o `get_state(thread_id)` do app encontra o snapshot mais recente rapidamente).

**Real agora:** 115 linhas, **15 `thread_id` distintos** (mais threads do que os 13 registros de
`analysis_record` — porque alguns casos de teste pausam no portão de revisão e nunca chegam a
`finalize`, então nunca geram uma linha em `analysis_record`, mas já geraram checkpoints). Dois
padrões de prefixo nos `thread_id`: `conv-*` (10 threads — testes de e2e/resume) e `t061-*` (5
threads — a rodada real T061).

Um caso típico como o `t061-...customer_legacy_id` tem **vários** checkpoints — um por superstep do
grafo (`interpret`, o fan-out paralelo dos 3 `collect_*`, `assess_risk`, `recommend`,
`human_review` antes e depois do `resume`, `finalize`). É por isso que 15 threads geram 115 linhas
aqui: em média ~7-8 checkpoints por caso.

### `checkpoint_blobs` — os valores grandes de cada canal de estado

| Coluna | Tipo | Para que serve |
|---|---|---|
| `thread_id`, `checkpoint_ns` | `TEXT` | Mesmo sentido de acima. |
| `channel` | `TEXT` | O nome do campo do `GraphState` sendo salvo — ex. `evidence`, `risk_history`, `structured_change`, `step_log`, `messages` (mensagens do agente investigador), `recommendations`, `review_actions`, `__start__`, `__pregel_tasks` (housekeeping interno do LangGraph). |
| `version` | `TEXT` | Versão desse canal (incrementa a cada escrita, para resolver merges). |
| `type` | `TEXT` | Formato de serialização — sempre `msgpack` aqui (o `JsonPlusSerializer` configurado em `src/dcra/persistence/serde.py`, com um *allowlist* explícito dos nossos tipos Pydantic: `ChangeRequest`, `StructuredChange`, `EvidenceItem`, `RiskAssessment`, etc.). |
| `blob` | `BYTEA` | O valor serializado em si (binário — não dá para ler direto via `SELECT`, mas dá para ver *quais* canais existem). |

PK composta: `(thread_id, checkpoint_ns, channel, version)`.

**Real agora:** 201 linhas. Contagem por canal (top): `step_log` (80), `__start__` (16),
`change_request` (15), `risk_history` (15), `evidence` (15), `risk` (15), `recommendations` (14),
`structured_change` (14), `review_actions` (11), `messages` (4 — só aparece quando o **agente
investigador** roda, porque é o histórico de mensagens ReAct dele), `__pregel_tasks` (2).

### `checkpoint_writes` — escritas pendentes por "tarefa" (nó) dentro de um superstep

| Coluna | Tipo | Para que serve |
|---|---|---|
| `thread_id`, `checkpoint_ns`, `checkpoint_id` | `TEXT` | Localizam o checkpoint. |
| `task_id` | `TEXT` | Identifica qual execução de nó gerou esta escrita (há um `task_id` por nó rodando dentro do superstep — é assim que 3 nós paralelos como `collect_asset`/`collect_deps`/`collect_usage` não colidem). |
| `idx` | `INTEGER` | Ordem da escrita dentro da tarefa. |
| `channel` | `TEXT` | Mesmo conceito de `checkpoint_blobs` — qual campo do estado está sendo escrito. |
| `type`, `blob` | `TEXT`/`BYTEA` | Formato + valor serializado. |
| `task_path` | `TEXT` | Caminho interno do LangGraph até essa tarefa (roteamento condicional). |

PK composta: `(thread_id, checkpoint_ns, checkpoint_id, task_id, idx)`.

**Real agora:** 544 linhas — a tabela mais "cheia", porque toda escrita intermediária passa por
aqui antes de virar um `checkpoint_blobs` consolidado. Canais mais escritos: `step_log` (108),
`status` (81), `evidence` (43 — reflete os 3 escritores paralelos por passada), canais
`branch:to:*` (roteamento condicional registrado explicitamente, ex. `branch:to:assess_risk`: 42),
`__resume__` (22 — uma por cada `Command(resume=...)`, ou seja, uma por decisão humana tomada).

### `checkpoint_migrations`

Uma tabela de **uma coluna** (`v INTEGER`, PK) — o "número da versão do schema" que o
`PostgresSaver` já aplicou nesse banco. **10 linhas** (`v = 0..9`): o LangGraph evoluiu seu próprio
schema de checkpoint 10 vezes e aplica essas migrações automaticamente em `saver.setup()`. Não
tem relação nenhuma com o produto — é puramente housekeeping da biblioteca.

---

## 3. Como tudo se conecta: seguindo um `thread_id`

Pegue o caso real acima (`t061-f1d28e6d-f0b0-4f3c-ad81-5412cfcbb814`) como exemplo de como navegar:

```sql
-- 1. O registro final (o que o produto mostra)
SELECT * FROM analysis_record WHERE id = 't061-f1d28e6d-f0b0-4f3c-ad81-5412cfcbb814';

-- 2. Cada "commit" de estado que esse caso passou, em ordem
SELECT checkpoint_id, parent_checkpoint_id, metadata->>'step' AS step
FROM checkpoints
WHERE thread_id = 't061-f1d28e6d-f0b0-4f3c-ad81-5412cfcbb814'
ORDER BY (metadata->>'step')::int;

-- 3. Quais canais de estado foram tocados em cada passo
SELECT checkpoint_id, channel, version
FROM checkpoint_blobs
WHERE thread_id = 't061-f1d28e6d-f0b0-4f3c-ad81-5412cfcbb814';
```

E, se `LANGSMITH_TRACING=true` estava ativo quando esse caso rodou, o **mesmo** `thread_id`
aparece como metadado do trace correspondente em smith.langchain.com (veja `LANGSMITH.md`) — é a
terceira janela para a mesma execução, essa com latência/tokens por passo.

---

## Como explorar você mesmo

O container já está de pé (`docker compose up -d`). Um shell interativo:

```bash
docker exec -it ws_datachange-postgres-1 psql -U dcra -d dcra
```

Comandos úteis dentro do `psql`:

```sql
\dt                                  -- listar tabelas
\d analysis_record                   -- descrever colunas de uma tabela
SELECT count(*) FROM analysis_record;
SELECT id, outcome, reviewed FROM analysis_record ORDER BY created_at DESC LIMIT 5;
SELECT change_request->>'raw_text', outcome FROM analysis_record;   -- extrair um campo do JSONB
```

`->>'campo'` extrai um valor de um `JSONB` como texto — é a forma mais rápida de "espiar" dentro
das colunas JSON sem escrever Python.
