# Known issues

The project is **complete and frozen** (see README → "Status"). This file
records defects that are known and intentionally left unfixed.

## "Reabrir um caso" — dropdown de casos em aberto vazio no ambiente publicado

**Onde:** `src/dcra/app/streamlit_app.py`, expander *"Reabrir um caso por id"* →
`selectbox` *"Casos em aberto"*, alimentado por `list_open_cases()`
(`src/dcra/graph/build.py`) via `_open_cases()` (`@st.cache_data(ttl=15)`).

**Sintoma:** no Cloud Run, o `selectbox` não lista casos que estão pausados no
portão de revisão. O campo de texto livre logo abaixo (reabrir informando o
`thread_id`) **funciona normalmente**. Localmente (docker-compose) a lista
aparece.

**Causa provável (não confirmada):** `PostgresSaver.list(None, ...)` varrendo o
checkpointer através do pooler do Neon numa instância fria do Cloud Run,
e/ou o cache `@st.cache_data` servindo `[]` de uma primeira renderização antes
de o pool aquecer. Não investigado a fundo.

**Impacto:** baixo — o fluxo de reabrir um caso continua acessível pelo
`thread_id` explícito. **Não será corrigido.**
