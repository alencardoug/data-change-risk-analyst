# DEMO — o roteiro para testar se tudo funciona

Este é o roteiro "oficial" do projeto para provar, em poucos minutos, que o fluxo inteiro
funciona ponta a ponta: interpretação → coleta paralela de evidências → risco determinístico →
recomendação da IA → pausa para revisão humana → decisão final registrada.

Pré-requisito: siga `GUIA_DE_USO.md` §"Como ligar tudo" primeiro (Postgres de pé, `.env`
preenchido, app rodando). Este arquivo assume que você já tem o Streamlit aberto no navegador.

## A demo de 2–3 minutos (a "vitrine" do projeto)

Este é o caso único que, sozinho, mostra as quatro coisas que valem a pena discutir numa
entrevista: separação determinístico/probabilístico, fan-out paralelo com reducer, e
interrupt/resume.

**Passo 1 — envie exatamente este texto** no campo "Proposed change":

```
Remove the column customer_legacy_id from the orders table
```

Preencha "Your name" com qualquer coisa (ex. `data.engineer`) e clique **Analyze**.

**Passo 2 — observe a seção "Steps"** crescer com estas linhas, nesta ordem:

```
interpret: DROP_COLUMN on orders
collect_asset: 1 item(s)
collect_deps: 2 item(s)
collect_usage: 1 item(s)
assess_risk: pass 1 → MEDIUM (REFERENCED_BY_VIEW, ACTIVELY_READ)
recommend: v1 PROCEED_WITH_MITIGATION (NORMAL)
```

Note que `collect_asset`, `collect_deps` e `collect_usage` aparecem como três linhas separadas mas
rodaram **em paralelo** (fan-out) — o grafo só segue para `assess_risk` depois que as três
terminam (fan-in). Isso é visível de forma ainda mais clara num trace do LangSmith — veja
`LANGSMITH.md`.

**Passo 3 — leia a seção "Evidence".** Você verá 4 itens, todos 🟢 `OBTAINED`: os metadados da
coluna (tipo `varchar`, ~1.8M linhas), duas views que dependem dela (`reporting.v_customer_orders`,
`reporting.v_legacy_bridge`) e um serviço que ainda a lê (`cs_lookup`, 4 leituras/dia).

**Passo 4 — leia "Risk: MEDIUM"** com dois fatores nomeados: `REFERENCED_BY_VIEW` e
`ACTIVELY_READ` (veja `REGRAS.md` para o porquê de cada um). Isso não veio do LLM — são regras
Python puras rodando sobre a evidência que você acabou de ler.

**Passo 5 — leia "Recommendation · 🤖 AI-generated"** — a IA lê a mesma evidência e os mesmos
fatores e escreve, em linguagem natural, `PROCEED_WITH_MITIGATION` com uma lista de mitigações
(atualizar as views, coordenar com o time do `cs_lookup`, etc.). Repare no rótulo "AI-generated
(non-binding)" — o sistema nunca deixa você confundir isso com uma decisão.

**Passo 6 — a execução pausou.** Como o risco é MEDIUM, o grafo não finaliza sozinho — ele chama
`interrupt()` e espera um humano. A seção "Human review" aparece com o risco, quantas revisões
ainda restam, e três botões.

**Passo 7 — clique "Approve".** A tela atualiza (o grafo foi *retomado* a partir do checkpoint
salvo, não recomeçado) e mostra: `Final record: APPROVED (human decision by data.owner)`, com a
nota "AI recommendation and human decision are recorded as separate fields" — o ponto central do
projeto: a IA recomenda, o humano decide, e os dois ficam gravados separadamente.

Isso é exatamente o registro real que você pode inspecionar em `INFO_BANCO.md` (§ "Top 3 exemplos
reais", exemplo 1) — essa demo já rodou de verdade contra `gpt-4o` durante o desenvolvimento
(tarefa T061) e o resultado ficou gravado no Postgres.

## Casos de contraste (rápidos, mostram os outros caminhos)

Depois do caso principal, vale rodar estes dois — cada um mostra um caminho *diferente* do grafo
sem precisar entender tudo de novo:

- **`add index on orders(customer_id)`** → risco **LOW** → auto-finaliza, **sem** portão de
  revisão (repare que "Human review" nunca aparece — o registro já sai como
  `Final record: AUTO_FINALIZED`).
- **`drop column orders.legacy_region`** → a coluna não existe no dataset simulado → evidência de
  metadados vem `UNAVAILABLE` com motivo `not_found` → risco **HIGH** automático, fator
  `ASSET_NOT_FOUND` → vai para revisão mesmo sem nenhuma dependência conhecida (o sistema nunca
  assume "seguro" quando não sabe o que a coluna é).

## Cenários completos S1–S8 (o roteiro de validação usado no desenvolvimento)

Estes 8 cenários (definidos em `specs/001-data-change-risk-review/quickstart.md`) cobrem **todo**
caminho possível do grafo. Cada um também existe como teste automatizado
(`tests/e2e/test_us*.py`) com um modelo falso e determinístico — rodá-los manualmente no Streamlit
é a versão "ver com os próprios olhos" do mesmo teste. Para exercitar todos, use
`GUIA_DE_USO.md`, que dá um passo a passo de cada um com mais detalhe de interação.

| # | O que testar | O que esperar |
|---|---|---|
| S1 | `add index on orders(customer_id)` | LOW → auto-finaliza |
| S2 | `drop column orders.customer_legacy_id` | MEDIUM → revisão → APPROVE → finaliza |
| S3 | S2, mas no portão clique "Return for revision", marque **"evidence missing"** | reavalia evidência, risco pode subir (MEDIUM→HIGH), gera recomendação v2, volta pro portão |
| S4 | `alter column orders.status` (com a fonte `usage` simulada como indisponível — veja nota abaixo) | evidência de uso vem `UNAVAILABLE` → lacuna detectada → agente investigador roda → recomendação com confiança `REDUCED` |
| S5 | `drop column ghost_table.foo` | ativo não encontrado → HIGH automático, `ASSET_NOT_FOUND` |
| S6 | Repita S2 e devolva para revisão **duas vezes** (qualquer nota) | na 2ª devolução, o botão "Return for revision" desaparece — só resta Approve/Reject |
| S7 | `make the thing better` (texto sem sentido) | erro de interpretação, "That could not be interpreted...", **nenhum registro é salvo** |
| S8 | Rode S2 até a tela de revisão, depois `docker compose restart`, depois use "Reopen a case by id" com o `thread_id` | o caso volta exatamente onde parou — prova que a pausa sobrevive a um restart do banco |

> **Nota sobre S4**: a fonte `usage` "desabilitada" é simulada em código
> (`dataset.disabled_sources`, `src/dcra/evidence/dataset.py:32`), não em UI — o Streamlit não
> expõe um jeito de ligar/desligar isso na tela. Para ver esse caminho de verdade, é mais fácil
> rodar o teste automatizado correspondente (`tests/e2e/test_us1_evidence_unavailable.py`) ou ler
> seu resultado — o comportamento (evidência UNAVAILABLE → agente investigador → confiança
> REDUCED) é o mesmo que S4 descreve.

## Onde ler o resultado depois

- **No app**: a resposta aparece na tela, seção por seção.
- **No banco**: `INFO_BANCO.md` mostra como consultar `analysis_record` pelo `thread_id`
  (aparece implicitamente — é o `id` do caso, visível se você guardar a URL/estado da sessão).
- **No LangSmith** (se `LANGSMITH_TRACING=true`): `LANGSMITH.md` explica como achar a mesma
  execução como um trace visual, com tempo e tokens gastos em cada passo.
