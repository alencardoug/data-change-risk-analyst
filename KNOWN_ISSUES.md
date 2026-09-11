# Known issues

The project is **complete and frozen** (see README → "Status"). This file
records defects that are known and intentionally left unfixed.

**Nenhum defeito em aberto no momento.**

## Resolvidos

### "Reabrir um caso" — dropdown de casos em aberto vazio no ambiente publicado (resolvido em 2026-09-11)

**Onde:** `src/dcra/app/streamlit_app.py`, expander *"Reabrir um caso por id"* →
`selectbox` *"Casos em aberto"*, alimentado por `list_open_cases()`
(`src/dcra/graph/build.py`) via `_open_cases()` (`@st.cache_data(ttl=15)`).

**Sintoma:** no Cloud Run, o `selectbox` deixava de listar casos pausados no
portão de revisão. O campo de texto livre logo abaixo (reabrir informando o
`thread_id`) sempre funcionou.

**Causa (confirmada por reprodução com `PostgresSaver` real):**
`list_open_cases()` chamava `checkpointer.list(None, limit=60)`, que ordena por
`checkpoint_id DESC` **globalmente** (todos os threads misturados), e cada
execução grava ~7 checkpoints. Depois de ~8 análises posteriores de outros
usuários, os checkpoints do caso pausado saíam da janela fixa de 60 linhas e o
caso sumia da lista — independente do estado do Neon. A primeira hipótese
(cold start do Neon / pooler) foi descartada: o problema persistia com o banco
acordado, e nem o pool (`prepare_threshold=0`, pre-ping) nem o `.list()` da lib
(`execute` + `fetchall`, sem cursor de servidor) dependem disso.

**Correção:** a janela começa em 60 linhas e dobra até encontrar pelo menos
3 casos em aberto (`min_open`), esgotar o checkpointer ou atingir 480 linhas
(`max_scan`, ~65 casos de retrospecto). Threads já inspecionados não são
reconsultados e um caso cujo checkpoint mais novo está `FINALIZED` é terminal
(pula o `get_state()`), então o custo extra fica limitado aos threads que ainda
podem estar abertos. Resultado ordenado do mais novo para o mais antigo pelo
`checkpoint_id` (uuid6), independente da ordem de enumeração do saver.
Testes: `tests/e2e/test_reopen_case.py` (MemorySaver) e
`tests/e2e/test_open_cases_postgres.py` (PostgresSaver, DB-gated).
