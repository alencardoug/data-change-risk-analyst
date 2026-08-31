"""Interface Streamlit do Analista de Risco de Mudança de Dados.

Executar:  uv run streamlit run src/dcra/app/streamlit_app.py

Mostra o fluxo avançando: interpretação → evidências (inclusive indisponíveis) → risco + fatores →
recomendação (rotulada como gerada por IA) → para MÉDIO/ALTO o portão de revisão (US2), para BAIXO
um registro finalizado automaticamente.

Observação: os rótulos de domínio (categorias de risco, disposições, etc.) são traduzidos apenas
na camada de exibição; os valores internos/persistidos permanecem em inglês.
"""

from __future__ import annotations

import re
import threading
import time

import streamlit as st

from dcra.config import Settings
from dcra.domain.models import ChangeRequest, InterpretationError
from dcra.evidence.dataset import default_dataset
from dcra.graph.build import (
    build_graph,
    get_state,
    is_awaiting_review,
    list_open_cases,
    pending_interrupt,
    resume,
    run,
)
from dcra.graph.deps import GraphDeps, production_deps
from dcra.graph.nodes import review_payload

# --------------------------------------------------------------------------------------
# Tabelas de tradução (somente exibição)
# --------------------------------------------------------------------------------------

_RISK_PT = {"LOW": "BAIXO", "MEDIUM": "MÉDIO", "HIGH": "ALTO"}

_OPERATION_PT = {
    "DROP_COLUMN": "REMOÇÃO DE COLUNA",
    "ALTER_COLUMN": "ALTERAÇÃO DE COLUNA",
    "ADD_INDEX": "ADIÇÃO DE ÍNDICE",
}

_DISPOSITION_PT = {
    "PROCEED": "PROSSEGUIR",
    "PROCEED_WITH_MITIGATION": "PROSSEGUIR COM MITIGAÇÃO",
    "DO_NOT_PROCEED": "NÃO PROSSEGUIR",
}

_CONFIDENCE_PT = {"NORMAL": "NORMAL", "REDUCED": "REDUZIDA"}

_EVIDENCE_KIND_PT = {
    "ASSET_METADATA": "METADADOS DO ATIVO",
    "DEPENDENCY": "DEPENDÊNCIA",
    "DOWNSTREAM_USAGE": "USO A JUSANTE",
}

_OUTCOME_PT = {
    "APPROVED": "APROVADO",
    "REJECTED": "REJEITADO",
    "AUTO_FINALIZED": "FINALIZADO AUTOMATICAMENTE",
}

_DECISION_PT = {"APPROVE": "APROVAR", "REJECT": "REJEITAR", "RETURN": "DEVOLVER"}

# Descrições dos fatores de risco, por código (o texto de origem vive nas regras de domínio).
_FACTOR_DESC_PT = {
    "ASSET_NOT_FOUND": "O ativo afetado não foi encontrado na fonte de evidências.",
    "INDEX_BUILD_CONTENTION": "O alvo do índice é intensamente lido; recomenda-se build online.",
    "ADD_INDEX_LOW_RISK": "Adição de índice sem contenção de leitura pesada listada.",
    "IN_PRIMARY_KEY": "A coluna participa da chave primária.",
    "IN_UNIQUE_CONSTRAINT": "A coluna participa de uma restrição de unicidade.",
    "INBOUND_FOREIGN_KEY": "Há chave(s) estrangeira(s) que referenciam esta coluna.",
    "REFERENCED_BY_VIEW": "Referenciada por visão(ões)/materialização(ões).",
    "ACTIVELY_READ": "Consumidor(es) a jusante ainda leem esta coluna.",
    "EVIDENCE_UNAVAILABLE": (
        "Parte das evidências de dependência/uso não pôde ser obtida; risco incerto."
    ),
    "NO_DEPENDENTS_OR_USAGE": "Sem dependentes e sem uso a jusante registrado.",
}

# Prefixo (nome do nó) de cada linha do log de etapas.
_STEP_PREFIX_PT = {
    "interpret": "Interpretação",
    "collect_asset": "Ativos da coleção",
    "collect_deps": "Dependências da coleção",
    "collect_usage": "Uso da coleção",
    "assess_risk": "Avaliação de risco",
    "reassess": "Reavaliação",
    "investigate": "Investigação",
    "recommend": "Recomendação",
    "human_review": "Revisão humana",
    "finalize": "Finalização",
}

# Frases fixas que aparecem no corpo das linhas do log de etapas.
_STEP_PHRASES_PT = [
    ("item(s)", "item(ns)"),
    ("pass ", "passo "),
    ("; evidence gap", "; lacuna de evidência"),
    ("evidence gap", "lacuna de evidência"),
    (
        "re-collecting evidence after 'evidence missing' feedback",
        "re-coletando evidências após feedback de 'evidência ausente'",
    ),
    ("failed — request not understood", "falhou — solicitação não compreendida"),
    ("agent added ", "agente adicionou "),
    ("(evidence missing)", "(evidência ausente)"),
    (" (auto, no human review)", " (automática, sem revisão humana)"),
    (" on ", " em "),
    ("consumer(s)", "consumidor(es)"),
    ("reads/day", "leituras/dia"),
    ("online build advised", "build online recomendado"),
]


def _pt_step(line: str) -> str:
    head, sep, tail = line.partition(":")
    key = head.strip()
    if key.startswith("collect_usage"):
        label = "Uso da coleção" + key[len("collect_usage"):]
    else:
        label = _STEP_PREFIX_PT.get(key, key)
    out = f"{label}{sep}{tail}" if sep else line
    # categoria de risco quando aparece como "→ MEDIUM" ou "risk now HIGH"
    out = re.sub(
        r"(→ |risk now )(LOW|MEDIUM|HIGH)",
        lambda m: m.group(1) + _RISK_PT[m.group(2)],
        out,
    )
    out = out.replace("risk now ", "risco agora ")
    # operação na linha de interpretação (\b evita atingir códigos como ADD_INDEX_LOW_RISK)
    out = re.sub(
        r"\b(DROP_COLUMN|ALTER_COLUMN|ADD_INDEX)\b",
        lambda m: _OPERATION_PT[m.group(1)],
        out,
    )
    # decisão de revisão (ex.: "human_review: APPROVE")
    out = re.sub(
        r"\b(APPROVE|REJECT|RETURN)\b",
        lambda m: _DECISION_PT[m.group(1)],
        out,
    )
    # disposição da recomendação (ex.: "recommend: v1 PROCEED_WITH_MITIGATION")
    out = re.sub(
        r"\b(PROCEED_WITH_MITIGATION|DO_NOT_PROCEED|PROCEED)\b",
        lambda m: _DISPOSITION_PT[m.group(1)],
        out,
    )
    # desfecho final (ex.: "finalize: AUTO_FINALIZED")
    out = re.sub(
        r"\b(AUTO_FINALIZED|APPROVED|REJECTED)\b",
        lambda m: _OUTCOME_PT[m.group(1)],
        out,
    )
    for src, dst in _STEP_PHRASES_PT:
        out = out.replace(src, dst)
    return out


def _how_finalized(actions) -> str:
    if not actions:
        return "finalizado automaticamente, sem revisão humana"
    return f"decisão humana por {actions[-1].reviewer}"


# --------------------------------------------------------------------------------------
# Página
# --------------------------------------------------------------------------------------

st.set_page_config(page_title="Analista de Risco de Mudança de Dados", layout="centered")

_INTRO_LEAD = (
    "Ferramenta corporativa com IA que ajuda uma empresa a decidir se uma mudança em um "
    "ativo de dados pode ser feita com segurança."
)
_INTRO_CONTEXT = (
    "**Contexto:** imagine, por exemplo, que alguém queira alterar uma tabela importante do "
    "Data Warehouse — o banco de dados estruturado da instituição: mudar o tipo de uma coluna, "
    "remover um campo, alterar uma regra ou modificar alguma estrutura usada por outros "
    "sistemas. Em uma empresa real, uma mudança aparentemente pequena pode quebrar dashboards, "
    "pipelines, relatórios financeiros ou aplicações. O projeto disponibiliza deterministicamente "
    "o “analista de risco automatizado” para 3 processos em colunas."
)


def _footer() -> None:
    st.caption("por Douglas Alencar")


def _intro_page() -> None:
    """Pré-página: apresenta o projeto antes da interface de análise."""
    st.title("Analista de Risco de Mudança de Dados")
    st.markdown(_INTRO_LEAD)
    st.markdown(_INTRO_CONTEXT)
    st.divider()
    if st.button("Começar", type="primary"):
        st.session_state["entered"] = True
        st.rerun()
    _footer()


# --------------------------------------------------------------------------------------
# Tabela `orders` — o Data Warehouse simulado que a ferramenta analisa
# --------------------------------------------------------------------------------------

_ORDERS_COL_ORDER = ["id", "customer_id", "customer_legacy_id", "status", "notes_internal"]

_ORDERS_COL_DESC = {
    "id": "Identificador único do pedido. É alvo da foreign key `fk_order_items_order` "
          "(itens do pedido) e é lido diariamente pelo job `warehouse_sync`.",
    "customer_id": "Cliente que fez o pedido. Lido intensamente pelo painel `ops_dashboard` "
                   "(~90 leituras/dia).",
    "customer_legacy_id": "Código do cliente no sistema legado, mantido para conciliação "
                          "durante a migração. Sustenta as views `reporting.v_customer_orders` "
                          "e `reporting.v_legacy_bridge` e ainda é consultado pelo serviço "
                          "`cs_lookup`.",
    "status": "Situação do pedido (NEW, PAID, SHIPPED, DELIVERED, CANCELLED, REFUNDED). "
              "Alimenta a view `reporting.v_open_orders`.",
    "notes_internal": "Anotações internas de operação, em texto livre. Sem dependentes nem "
                      "uso a jusante registrado.",
}

# (id, customer_id, customer_legacy_id, status, notes_internal) — None = NULL
_ORDERS_ROWS = [
    (48201, 10293, "LGC-0007742", "DELIVERED", None),
    (48202, 11841, None, "PAID", "Cliente pediu antecipação do envio."),
    (48203, 10022, "LGC-0003118", "SHIPPED", None),
    (48204, 12507, None, "NEW", None),
    (48205, 10293, "LGC-0007742", "CANCELLED", "Cancelado a pedido do cliente (SAC #8821)."),
    (48206, 11310, "LGC-0009004", "DELIVERED", None),
    (48207, 13288, None, "PAID", None),
    (48208, 10761, "LGC-0002251", "REFUNDED", "Produto com defeito; reembolso total."),
    (48209, 12044, "LGC-0006689", "SHIPPED", None),
    (48210, 11987, None, "DELIVERED", None),
    (48211, 10450, "LGC-0001120", "NEW", "Endereço corrigido pelo SAC."),
    (48212, 12903, "LGC-0008337", "PAID", None),
    (48213, 11102, None, "SHIPPED", None),
    (48214, 10293, "LGC-0007742", "DELIVERED", None),
    (48215, 13571, "LGC-0010885", "CANCELLED", "Pagamento não confirmado em 48h."),
]

_ORDERS_SAMPLE = [dict(zip(_ORDERS_COL_ORDER, row, strict=True)) for row in _ORDERS_ROWS]


def _orders_schema_md() -> str:
    """Tabela de estrutura montada a partir do dataset simulado (não pode divergir das regras)."""
    ds = default_dataset()
    rows = ["| Coluna | Tipo | Restrições | Para que serve |", "|---|---|---|---|"]
    for short in _ORDERS_COL_ORDER:
        f = ds.columns.get(f"orders.{short}")
        if f is None:
            continue
        restr: list[str] = []
        if f.in_primary_key:
            restr.append("**PK**")
        if not f.is_nullable:
            restr.append("NOT NULL")
        if f.in_unique_constraint:
            restr.append("UNIQUE")
        fk = next(
            (d["dependent"] for d in f.dependencies
             if d.get("dependent_type") == "foreign_key"),
            None,
        )
        if fk:
            restr.append(f"alvo de FK (`{fk}`)")
        cell = " · ".join(restr) if restr else "aceita NULL"
        rows.append(f"| `{short}` | `{f.data_type}` | {cell} | {_ORDERS_COL_DESC[short]} |")
    return "\n".join(rows)


def _orders_table_page() -> None:
    """Página 'Ver tabela': botão voltar + cabeçalho + 15 linhas de exemplo de `orders`."""
    if st.button("← Voltar para a aplicação"):
        st.session_state["view"] = "app"
        st.rerun()
    st.title("Tabela `orders`")
    st.caption(
        "Amostra do Data Warehouse simulado que a ferramenta analisa — 5 colunas, "
        "15 linhas de exemplo. Células vazias = NULL."
    )
    st.dataframe(
        _ORDERS_SAMPLE,
        hide_index=True,
        use_container_width=True,
        column_order=_ORDERS_COL_ORDER,
    )
    _footer()


if not st.session_state.get("entered"):
    _intro_page()
    st.stop()

if st.session_state.get("view") == "orders_table":
    _orders_table_page()
    st.stop()

_head, _about = st.columns([5, 1])
_head.title("Analista de Risco de Mudança de Dados")
if _about.button("Sobre", help="Voltar à página de apresentação"):
    st.session_state["entered"] = False
    st.rerun()
st.caption(_INTRO_LEAD)


@st.cache_resource
def _graph():
    settings = Settings.from_env()
    try:
        deps: GraphDeps = production_deps(settings, default_dataset())
    except Exception as exc:  # sem chave de API / sem BD — degrada com mensagem clara
        st.warning(
            f"LLM/BD não totalmente configurado ({exc}); configure o .env para executar "
            "análises reais."
        )
        raise
    return build_graph(deps, checkpointer=_checkpointer(settings))


def _checkpointer(settings: Settings):
    from dcra.persistence.checkpointer import make_checkpointer

    return make_checkpointer(settings.database_url)


_EXAMPLES = [
    "remover coluna customer_legacy_id na tabela orders",
    "add index on orders(customer_id)",
    "crie uma tabela para que tenhamos um mundo melhor",
    "alterar coluna tabela_fantasma.boo",
]

with st.expander("Exemplos de uso - para preencher no campo Mudança proposta"):
    # os `_` são escapados para não virarem itálico no Markdown (mudaria a fonte)
    st.markdown("\n".join(f"- {ex}" for ex in _EXAMPLES).replace("_", r"\_"))

with st.form("submit"):
    text = st.text_input(
        "Mudança proposta",
        placeholder="ex.: Remover a coluna customer_legacy_id da tabela orders",
    )
    who = st.text_input("Seu nome", value="data.engineer")
    _btn_col, _status_col = st.columns([1, 3], vertical_alignment="center")
    submitted = _btn_col.form_submit_button("Analisar")
    _processing_slot = _status_col.empty()


def _run_with_counter(cr: ChangeRequest, slot) -> dict:
    """Roda a análise numa thread e atualiza `slot` com "Processando… Ns" a cada segundo."""
    graph = _graph()  # erros de configuração aparecem aqui, como antes
    box: dict = {}

    def _work() -> None:
        try:
            box["state"] = run(graph, cr)
        except InterpretationError:
            box["state"] = {"error": "interpretation_failed"}
        except Exception as exc:  # propaga na thread principal
            box["exc"] = exc

    worker = threading.Thread(target=_work, daemon=True)
    worker.start()
    started = time.monotonic()
    while worker.is_alive():
        slot.markdown(f"⏳ Processando… {int(time.monotonic() - started) + 1}s")
        time.sleep(0.2)
    worker.join()
    slot.empty()
    if "exc" in box:
        raise box["exc"]
    return box["state"]


if submitted and text.strip():
    cr = ChangeRequest(raw_text=text.strip(), submitted_by=who or "anonymous")
    st.session_state["thread_id"] = cr.id
    st.session_state["submitted_by"] = cr.submitted_by
    st.session_state["state"] = _run_with_counter(cr, _processing_slot)

state = st.session_state.get("state")
if state:
    if state.get("error"):
        st.error(
            "Isso não pôde ser interpretado como uma mudança de dados reconhecida. Reformule "
            "(ex.: “remover coluna orders.status”, “adicionar índice em orders(customer_id)”)."
        )
    else:
        st.subheader("Etapas")
        for line in state.get("step_log", []):
            st.write("•", _pt_step(line))

        st.subheader("Evidências")
        for e in state.get("evidence", []):
            tag = "🟢" if e.status.value == "OBTAINED" else "🟠 indisponível"
            kind = _EVIDENCE_KIND_PT.get(e.kind.value, e.kind.value)
            st.write(f"{tag} · **{kind}** · {e.key} · _{e.source}_")
            if e.payload:
                st.json(e.payload, expanded=False)

        risk = state.get("risk")
        if risk:
            st.subheader(f"Risco: {_RISK_PT.get(risk.category.value, risk.category.value)}")
            for f in risk.factors:
                sev = _RISK_PT.get(f.severity.value, f.severity.value)
                desc = _FACTOR_DESC_PT.get(f.code, f.description)
                st.write(f"- **{f.code}** ({sev}) — {desc}")

        recs = state.get("recommendations", [])
        if recs:
            r = recs[-1]
            st.subheader("Recomendação  ·  🤖 Gerada por IA (não vinculante)")
            disp = _DISPOSITION_PT.get(r.disposition.value, r.disposition.value)
            conf = _CONFIDENCE_PT.get(r.confidence.value, r.confidence.value)
            st.write(f"**{disp}** · confiança {conf}")
            st.write(r.rationale)
            if r.mitigations:
                st.write("Mitigações:", ", ".join(r.mitigations))

        thread_id = st.session_state.get("thread_id")
        payload = pending_interrupt(state)
        if payload is None and thread_id and not state.get("outcome"):
            try:
                if is_awaiting_review(_graph(), thread_id):
                    payload = review_payload(state)
            except Exception:
                payload = None

        if state.get("outcome"):
            actions = state.get("review_actions", [])
            how = _how_finalized(actions)
            outcome = _OUTCOME_PT.get(state["outcome"].value, state["outcome"].value)
            st.success(f"Registro final: {outcome} ({how})")
            if actions:
                st.caption(
                    "A recomendação da IA e a decisão humana são registradas como campos "
                    "separados."
                )

        elif payload is not None:
            st.divider()
            st.subheader("Revisão humana")
            cat = _RISK_PT.get(payload["risk"]["category"], payload["risk"]["category"])
            st.caption(
                f"Risco {cat} · revisões restantes {payload['revisions_remaining']}"
            )
            reviewer = st.text_input(
                "Nome do revisor - sessão a ser separar (V2)",
                value=st.session_state.get("submitted_by", "data.owner"),
                disabled=True,
            )
            col_a, col_b, col_c = st.columns(3)
            decided = None
            if col_a.button("Aprovar", use_container_width=True):
                decided = {"decision": "APPROVE", "reviewer": reviewer}
            if col_b.button("Rejeitar", use_container_width=True):
                decided = {"decision": "REJECT", "reviewer": reviewer}
            if "RETURN" in payload["options"]:
                note = st.text_area("Devolver com uma observação", key="rn")
                miss = st.checkbox("Marcar: evidência ausente (reexecuta a avaliação de risco)")
                if col_c.button("Devolver para revisão", use_container_width=True):
                    decided = {
                        "decision": "RETURN", "reviewer": reviewer,
                        "note": note, "evidence_missing": miss,
                    }
            if decided is not None:
                st.session_state["state"] = resume(_graph(), thread_id, decided)
                st.rerun()

@st.cache_data(ttl=15, show_spinner=False)
def _open_cases(db_url: str | None) -> list[tuple[str, str]]:
    # `db_url` is the cache key (a plain str) so the result is reused across reruns; ttl bounds
    # staleness. `_graph()` is itself a cached resource, so this is a dict lookup plus one
    # checkpointer scan, not a graph rebuild.
    return list_open_cases(_graph())


def _reopen(tid: str) -> None:
    st.session_state["thread_id"] = tid
    st.session_state["state"] = get_state(_graph(), tid)
    st.rerun()


with st.expander("Reabrir um caso por id"):
    try:
        cases = _open_cases(Settings.from_env().database_url)
    except Exception:
        cases = []

    if cases:
        st.caption("Casos aguardando revisão (mais recentes):")
        labels = {label: tid for tid, label in cases}
        choice = st.selectbox("Casos em aberto", list(labels), index=None,
                              placeholder="Selecione um caso…")
        if st.button("Reabrir selecionado", disabled=choice is None):
            _reopen(labels[choice])
        st.divider()

    tid = st.text_input("Ou informe o thread_id")
    if st.button("Reabrir") and tid:
        try:
            _reopen(tid.strip())
        except Exception as exc:
            st.error(f"Não foi possível reabrir: {exc}")

with st.expander("Tabela `orders` — o Data Warehouse simulado"):
    st.markdown(
        "A ferramenta avalia mudanças propostas nesta tabela. Ela é simulada em código "
        "(`dcra.evidence.dataset`) — não existe um Postgres `orders` real —, mas a estrutura "
        "e a linhagem abaixo são exatamente o que alimenta a análise de risco."
    )
    st.markdown(_orders_schema_md())
    if st.button("Ver tabela", type="primary"):
        st.session_state["view"] = "orders_table"
        st.rerun()

st.divider()
_footer()
