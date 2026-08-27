# CICLO.md — O ciclo completo de revisão

> Documento de discovery. Explica **o que é** o ciclo de revisão humana escolhido para o V0
> (ADR-011) e **como ele vai funcionar**. Não é especificação nem plano — serve de contexto
> para `/speckit-specify` e `/speckit-clarify`.

---

## Em uma frase

É o workflow permitir que o revisor **devolva** a recomendação com um comentário, o sistema
**regenerar** a recomendação levando esse comentário em conta, e **voltar** a pausar para uma
nova revisão — repetindo isso um número limitado de vezes até o revisor aprovar ou rejeitar.

---

## Onde isso vive, tecnicamente

O LangGraph é uma **máquina de estados**. Existe um objeto de estado — pense nele como uma
**pasta de processo** — que todo nó lê e escreve. O fluxo normal é:

```
interpretar → coletar evidências → avaliar risco → (talvez) agente investigador
    → redigir recomendação → REVISÃO HUMANA (pausa)
```

Na **REVISÃO HUMANA** o grafo executa `interrupt()`: a execução **para de verdade**. O estado
inteiro é serializado num **checkpoint** (no PostgreSQL, ADR-012) identificado por um
`thread_id`. O processo não está "esperando numa variável na memória" — ele está salvo em
disco. Você pode fechar a aplicação, voltar amanhã, e retomar o mesmo `thread_id` do ponto
exato.

O revisor então escolhe uma de três saídas:

| Escolha | Para onde o grafo vai |
|---|---|
| **Aprovar** | → nó `finalizar` (status APROVADO) → FIM |
| **Rejeitar** | → nó `finalizar` (status REJEITADO) → FIM |
| **Pedir revisão** | carrega uma **nota em texto livre** → grafo retoma → aresta condicional **de volta** para `redigir recomendação` → regenera → **REVISÃO HUMANA de novo** |

Essa aresta que volta para um nó anterior **é o loop**. E há uma trava: um contador
`revision_count` no estado. Depois de N devoluções (padrão: 2), a opção "pedir revisão" some —
o revisor é obrigado a aprovar ou rejeitar. Sem isso o loop poderia girar para sempre.

O estado **acumula**: cada nota e cada versão da recomendação vão para uma lista
(`revision_history`) dentro da pasta de processo. Como as escritas aqui são sequenciais, um
`append` simples basta — mas é exatamente o ponto onde, se um dia houvesse dois ramos
escrevendo ao mesmo tempo, você precisaria de um *reducer*. Bom lugar para aprender o
conceito.

---

## Que conceitos de LangGraph isso exercita (e o que você defende em entrevista)

- **Checkpoint + `thread_id`** — a pausa é persistência real, não um modal de UI.
  "Como você retomaria um workflow interrompido?" → você mostra a linha no Postgres.
- **`interrupt` / `resume`** — `interrupt()` no nó de revisão; retomada com a decisão humana
  injetada no estado.
- **Aresta condicional / routing determinístico** — depois da revisão, um roteador **em
  código** lê o campo `decision` e escolhe aprovar/rejeitar/revisar. **O LLM não decide se há
  loop** — quem decide é o humano + o código.
- **Loop com guarda de terminação** — `revision_count < MAX` no roteador.
- **Estado como contrato** — a nota tem que cair num campo definido; o nó de recomendação tem
  que saber ler `revision_history`.

---

## A analogia — a mesa de análise de alvará na prefeitura

Você protocola um pedido de alvará (a *change request*). Um atendente preenche o formulário
padronizado a partir da sua descrição (nó `interpretar`). Pesquisadores puxam a matrícula do
imóvel, o mapa de zoneamento e as servidões de passagem das concessionárias (coleta de
evidências: ativo / dependências / uso). Um avaliador carimba **BAIXO / MÉDIO / ALTO** e
grampeia uma **lista dos porquês** (os fatores). Se falta informação, um fiscal vai a campo
olhar (agente investigador). Um técnico escreve um parecer (a recomendação).

Aí a pasta **cai na caixa de entrada do oficial revisor e para ali**. Nada acontece até ele
agir. A pasta inteira — todos os documentos — fica num arquivo numerado na sala de arquivos
(**isso é o checkpoint no Postgres; o número do processo é o `thread_id`**). A prefeitura pode
fechar no fim de semana; na segunda a pasta está exatamente onde estava.

O oficial tem um carimbo de três faces:

- **DEFERIDO** → a pasta vai para o arquivo como *encerrada-deferida*. Fim.
- **INDEFERIDO** → idem, *encerrada-indeferida*. Fim.
- **BAIXADO EM DILIGÊNCIA** → ele grampeia um bilhete na pasta ("o requerente não declarou a
  servidão no lado norte") e a manda **de volta para a mesa do técnico** — não para os
  pesquisadores. O técnico reescreve o parecer levando o bilhete em conta e devolve para a
  caixa do oficial. **O número do processo nunca muda; a pasta só engorda.**

E há uma regra pregada na parede: **um processo só pode ser baixado em diligência duas
vezes.** Na terceira passagem o oficial tem que deferir ou indeferir — chega de vai-e-volta.
Essa é a guarda do loop.

O que a analogia deixa concreto:

- A pausa **não é cosmética** — o trabalho realmente para e o estado está no arquivo físico
  (disco).
- "Baixado em diligência" volta para uma **etapa específica** (o parecer), não para o começo —
  esse é o alvo da aresta condicional.
- **Qual** carimbo usar é decisão **humana**; encaminhar a pasta que voltou é **mecânico**
  (roteador determinístico).
- A regra "duas vezes no máximo" está **na parede** (no código), não na cabeça do técnico
  (não no prompt).

---

## Passo a passo de uma execução real

1. **Data engineer** submete: *"Remover `customer_legacy_id` de `orders`."*
2. Grafo roda interpretar → coletar → avaliar (**MÉDIO**; fatores:
   `[referenciada por 2 views, sem FK, última leitura há 8 dias]`) → recomendar
   (*"Prosseguir com janela de depreciação de 2 semanas"*).
3. Nó `revisao_humana` chama `interrupt()`. Controle volta para a app. Estado salvo no
   Postgres sob o thread `chg-2026-0042`. No LangSmith o trace aparece terminando num
   interrupt.
4. UI (Streamlit) mostra risco + fatores + recomendação + 3 botões.
5. **Data owner** clica **Pedir revisão** e digita: *"as views `billing_monthly` e
   `cs_lookup` leem essa coluna toda noite — não estão na sua lista."*
6. App retoma com `{decision: "revise", note: "..."}`. Grafo re-hidrata do checkpoint.
7. Roteador determinístico: `decision == "revise"` e `revision_count (0) < 2` → aresta para
   `recomendar`. `revision_count → 1`, nota anexada ao `revision_history`.
8. Nó `recomendar` regenera com a nota no contexto → novo parecer (*"dependência de billing
   eleva para ALTO; exigir aprovação do time de billing antes"*).
9. Volta para `revisao_humana`, `interrupt()` de novo. Novo checkpoint, **mesmo thread**.
10. **Data owner** clica **Aprovar**. Retoma com `{decision: "approve"}`. Roteador →
    `finalizar`. Registro final gravado no Postgres, status APROVADO, histórico completo
    anexado. FIM.

---

## Pendente para o `/speckit-clarify`

A nota de revisão realimenta **só** o nó `recomendar`, ou também re-dispara `avaliar risco`
(ou o agente investigador)?

**Recomendação:** só `recomendar` por padrão; re-dispara o resto apenas se o humano marcar
explicitamente *"falta evidência"*. No exemplo acima, o técnico "subiu para ALTO" por conta
própria no texto — se você quer que o **carimbo de risco** mude formalmente, aí precisa
re-rodar `avaliar risco`.

---

## Decisões relacionadas

- **ADR-011** — este ciclo completo (loop no grafo) com guarda `revision_count` máx. 2.
- **ADR-005** — human-in-the-loop como estado de workflow (`interrupt`/`resume`).
- **ADR-012** — PostgreSQL como checkpointer desde o incremento 1 (torna a pausa/retomada
  real e demonstrável; permite inspecionar o estado serializado por `thread_id`).
- **ADR-013** — LangSmith tracing obrigatório (permite ver onde o interrupt ocorreu, o loop de
  tool-calling do agente, tokens e latência).
