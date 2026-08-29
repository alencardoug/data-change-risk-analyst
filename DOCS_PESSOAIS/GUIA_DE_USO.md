# GUIA_DE_USO — exemplos para testar tudo

Um catálogo de entradas para o campo "Proposed change" do Streamlit, organizado por **o que cada
uma exercita**, para você conseguir "bater" em toda regra de risco, todo caminho do grafo e todo
recurso do projeto sem precisar ler o código primeiro. Comece por `DEMO.md` se quiser só o roteiro
curto — este arquivo é o "modo exploração livre".

Toda a evidência simulada vem de `src/dcra/evidence/dataset.py` — só existem 5 colunas conhecidas
no "banco fictício" da tabela `orders`: `customer_legacy_id`, `notes_internal`, `status`, `id`,
`customer_id`. Qualquer outra coluna/tabela é "desconhecida" de propósito (para testar o caminho
`ASSET_NOT_FOUND`).

## Como ligar tudo

```bash
cp .env.example .env          # preencha OPENAI_API_KEY (e LANGSMITH_API_KEY, se tiver)
docker compose up -d           # ou: make db
uv sync                        # ou: make sync
uv run streamlit run src/dcra/app/streamlit_app.py   # ou: make app
```

Se preferir, `make help` lista todos os atalhos (`make app`, `make db`, `make test`, `make graph`).

---

## 1. Um exemplo para cada categoria de risco

| Categoria | Entrada | Fator(es) esperado(s) | O que prova |
|---|---|---|---|
| **LOW** | `drop column orders.notes_internal` | `NO_DEPENDENTS_OR_USAGE` | coluna genuinamente sem uso → seguro, auto-finaliza |
| **LOW** | `add index on orders(customer_id)` | `ADD_INDEX_LOW_RISK` | criar índice é de baixo risco por padrão |
| **MEDIUM** | `drop column orders.status` | `REFERENCED_BY_VIEW` | referenciada por uma view (`reporting.v_open_orders`), mas sem leitura ativa (0 leituras/dia) |
| **MEDIUM** | `drop column orders.customer_legacy_id` | `REFERENCED_BY_VIEW` + `ACTIVELY_READ` | o caso "canônico" da demo — dois fatores MEDIUM ao mesmo tempo |
| **HIGH** | `drop column orders.id` | `IN_PRIMARY_KEY` + `INBOUND_FOREIGN_KEY` | quebra a integridade relacional do banco (chave primária referenciada por `order_items`) |
| **HIGH** | `drop column orders.legacy_region` | `ASSET_NOT_FOUND` | coluna que não existe no catálogo — o sistema nunca assume "seguro" quando não conhece o ativo |

## 2. Testando os dois tipos de operação

- **`DROP_COLUMN`** / **`ALTER_COLUMN`** — qualquer um dos exemplos acima. Frases que funcionam
  igualmente: `"drop column orders.status"`, `"remove the status column from orders"`, `"alter
  column orders.status to make it nullable"` — a interpretação é feita pelo LLM (veja
  `LANGCHAIN.md`), então frases naturais em inglês funcionam, não só a sintaxe SQL-like.
- **`ADD_INDEX`** — precisa de uma coluna-alvo. Ex.: `"add index on orders(customer_id)"`
  (LOW, 90 leituras/dia < limiar de 100) — não há no dataset simulado nenhuma coluna acima do
  limiar de contenção (100 leituras/dia), então `INDEX_BUILD_CONTENTION` (MEDIUM) não é
  alcançável via UI com os dados atuais; ele é coberto pelo teste unitário
  `tests/unit/test_risk_rules.py` com um dataset customizado.

## 3. Testando o portão de revisão humana (qualquer entrada MEDIUM/HIGH)

Envie `drop column orders.customer_legacy_id` (ou qualquer MEDIUM/HIGH da tabela acima) e, na
seção "Human review":

- **Approve** → `outcome = APPROVED`, `reviewed = true`.
- **Reject** → `outcome = REJECTED`, `reviewed = true`. Repare que rejeitar **não** apaga o caso —
  ele ainda vira um `AnalysisRecord` completo, só que com veredito negativo. Um "não" é uma
  decisão registrada tanto quanto um "sim".
- **Return for revision** (nota livre, sem marcar "evidence missing") → o grafo volta direto para
  `recommend` com sua nota como contexto extra; observe a recomendação de v1 virar v2, geralmente
  mudando de texto mas **mantendo a mesma categoria de risco** (a evidência não mudou).
- **Return for revision, marcando "Mark: evidence missing"** → o grafo volta para
  `reassess_gate`, **re-coleta as três evidências em paralelo de novo**, reavalia o risco do zero
  (`pass_number` sobe para 2) e só então gera uma nova recomendação. Escreva na nota algo que
  simule uma informação nova, ex.: `"billing_monthly and cs_lookup also read it nightly"` — isso
  não altera o dataset simulado (que é fixo), mas mostra o *caminho* de reavaliação completo.
- **Devolva duas vezes seguidas** (qualquer modo) → na terceira vez que a tela de revisão aparecer,
  repare que o botão "Return for revision" **sumiu** — só restam Approve/Reject. Isso é o limite
  `DCRA_REVISION_LIMIT` (padrão 2) sendo aplicado; a UI esconde a opção, e o roteador do grafo
  (`route_after_review`) também recusaria uma 3ª devolução mesmo que a UI não escondesse (é um
  "cinto de segurança" duplo — veja `src/dcra/graph/nodes.py:210`).

## 4. Testando a interpretação (e sua falha)

- Frases razoáveis mas fora de sintaxe SQL: `"we need to remove the notes_internal field from
  orders"` — deve interpretar corretamente mesmo assim.
- Entrada sem sentido: `"make the thing better"` → o LLM tenta, falha a validação Pydantic duas
  vezes (há um retry automático com feedback do erro — veja `LANGCHAIN.md`), e você vê a mensagem
  de erro "That could not be interpreted as a recognised data change". **Nenhum registro é salvo**
  no banco para esse caso — confirme rodando a contagem de `analysis_record` antes e depois
  (`INFO_BANCO.md`).

## 5. Testando pausa + retomada (sobrevive a restart)

1. Envie um caso MEDIUM/HIGH e pare na tela "Human review" (não clique em nada ainda).
2. Copie o texto de estado da sessão ou simplesmente confie que o caso está pausado — o
   `thread_id` é o `id` do `ChangeRequest` (um UUID).
3. Reinicie o Postgres: `docker compose restart`.
4. No expander **"Reopen a case by id"**, cole o `thread_id` (para descobri-lo sem guardar
   manualmente, veja a dica no fim desta seção) e clique **Reopen**.
5. O caso volta exatamente para a tela de revisão, com a mesma avaliação de risco e recomendação —
   nada foi perdido, porque cada passo do grafo já estava gravado em Postgres antes do restart
   (as tabelas `checkpoint_*` — veja `INFO_BANCO.md` e `LANGGRAPH.md`).

> **Dica para achar o `thread_id`**: rode `docker exec ws_datachange-postgres-1 psql -U dcra -d dcra
> -c "SELECT DISTINCT thread_id FROM checkpoints ORDER BY thread_id DESC LIMIT 5;"` logo depois de
> enviar o caso — o mais recente por ordem de criação é o seu.

## 6. Testando o incremento V1 (MCP)

Por padrão a leitura de "uso downstream" é uma função Python local. Ligando a variável de
ambiente, ela passa a rodar como uma chamada de rede (na prática, um subprocesso local) via
**Model Context Protocol**:

```bash
DCRA_USAGE_VIA_MCP=1 uv run streamlit run src/dcra/app/streamlit_app.py
```

Rode o mesmo caso `drop column orders.customer_legacy_id` de novo. O resultado deve ser
**idêntico** ao modo local — mesma evidência, mesmo risco, mesma recomendação — só que na seção
"Steps" a linha muda de `collect_usage: 1 item(s)` para `collect_usage (via MCP): 1 item(s)`.
Isso prova que MCP aqui é só uma *mudança de onde a tool roda*, não uma mudança de comportamento —
veja `docs/mcp.md` e `LANGCHAIN.md` (seção MCP) para o porquê disso importar em entrevistas.

Para ver o servidor MCP isoladamente (sem o app), rode `python -m dcra.mcp.server` — ele fica
esperando conexões stdio; use Ctrl+C para sair.

## 7. Rodando os testes automatizados (a versão "sem clicar")

```bash
uv run pytest tests/unit tests/e2e -q          # ou: make test — determinístico, sem API key/DB
RUN_LLM_TESTS=1 uv run pytest tests/llm_integration -q   # ou: make llm-test — chamadas reais ao gpt-4o
DATABASE_URL=postgresql://dcra:dcra@localhost:5432/dcra uv run pytest tests/unit/test_repository.py
uv run pytest tests/mcp -q                     # round-trip do modo MCP vs. leitor local
```

Cada arquivo em `tests/e2e/test_us*.py` corresponde a um cenário S1–S8 de `DEMO.md`, mas rodado
com um **modelo falso** (determinístico, sem custo, sem chave) — é a mesma jornada, só que
verificada por asserção em vez de olho humano. Ótimo para ver rapidamente "o que exatamente esse
cenário garante" — abra o arquivo de teste correspondente e leia as asserções.

## 8. Explorando o resultado nos três lugares

Depois de rodar qualquer caso, os mesmos dados aparecem em três formas diferentes — vale comparar:

1. **Na tela** — o jeito "produto".
2. **No banco** — `INFO_BANCO.md` mostra como consultar `analysis_record` e as tabelas de
   checkpoint pelo `thread_id`.
3. **No LangSmith** (se ativo) — `LANGSMITH.md` mostra como achar o mesmo `thread_id` como um
   trace visual com tempo e custo por passo.

## 9. Ver o grafo sem rodar nada

```bash
make graph
```

Imprime o grafo compilado como Mermaid (o mesmo diagrama que está no `LEIAME.md`) — útil para
comparar a topologia declarada em `src/dcra/graph/build.py` com o que você observou rodando os
casos acima.
