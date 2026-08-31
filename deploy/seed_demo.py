"""Seed `analysis_record` with 15 synthetic-but-coherent demo cases.

Purpose: give a table view (for a portfolio / a data recruiter) real-shaped
rows to look at. Data is synthetic per the project constitution.

Coherence: `evidence` and `risk_assessments` are computed by the *real*
tools and rules (`dcra.evidence.tools`, `dcra.rules.risk`) against
`default_dataset()`, so the risk factors always match the evidence. Only the
LLM-authored parts (recommendation prose, reviewer notes) are hand-written.

Idempotent: fixed ids `demo-01`..`demo-15`; `PostgresRepository.save` UPSERTs.

Run:
    DATABASE_URL='postgresql://…?sslmode=require' uv run python deploy/seed_demo.py
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from dcra.domain.enums import (
    Confidence,
    Disposition,
    Operation,
    Outcome,
    ReviewDecision,
)
from dcra.domain.models import (
    AnalysisRecord,
    ChangeRequest,
    Recommendation,
    ReviewAction,
    StructuredChange,
)
from dcra.evidence.dataset import default_dataset
from dcra.evidence.tools import (
    read_asset_metadata,
    read_dependencies,
    read_downstream_usage,
)
from dcra.persistence.repository import PostgresRepository
from dcra.rules import risk as risk_rules

_DS = default_dataset()


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


def _target_col(sc: StructuredChange) -> str:
    return sc.target_column or (sc.index_columns[0] if sc.index_columns else "")


def _evidence(sc: StructuredChange) -> list:
    col = _target_col(sc)
    ev = read_asset_metadata(_DS, sc.target_table, col or None)
    if col:
        ev += read_dependencies(_DS, sc.target_table, col)
        ev += read_downstream_usage(_DS, sc.target_table, col)
    return ev


def _step_log(sc, risk, recs, actions, reviewed, outcome) -> list[str]:
    ev = _evidence(sc)
    n = {"ASSET_METADATA": 0, "DEPENDENCY": 0, "DOWNSTREAM_USAGE": 0}
    for e in ev:
        n[e.kind.value] += 1
    lines = [
        f"interpret: {sc.operation.value} on {sc.target_table}",
        f"collect_asset: {n['ASSET_METADATA']} item(s)",
        f"collect_deps: {n['DEPENDENCY']} item(s)",
        f"collect_usage: {n['DOWNSTREAM_USAGE']} item(s)",
        f"assess_risk: pass 1 → {risk.category.value} "
        f"({', '.join(f.code for f in risk.factors)})",
    ]
    for i, r in enumerate(recs):
        lines.append(
            f"recommend: v{r.version} {r.disposition.value} ({r.confidence.value})"
        )
        if i < len(actions):
            a = actions[i]
            lines.append(
                f"human_review: {a.decision.value}"
                + (" (evidence missing)" if a.evidence_missing else "")
            )
    lines.append(
        f"finalize: {outcome.value}" + ("" if reviewed else " (auto, no human review)")
    )
    return lines


def _sc(operation, table, column=None, index_columns=None, alter_detail=None):
    return StructuredChange(
        operation=operation,
        target_table=table,
        target_column=column,
        index_columns=index_columns or [],
        alter_detail=alter_detail,
        confidence=0.9,
    )


def _rec(version, disposition, rationale, mitigations=None, confidence=Confidence.NORMAL,
         note=None):
    return Recommendation(
        version=version,
        disposition=disposition,
        rationale=rationale,
        mitigations=mitigations or [],
        confidence=confidence,
        prompted_by_note=note,
        ai_generated=True,
    )


DROP, ALTER, INDEX = Operation.DROP_COLUMN, Operation.ALTER_COLUMN, Operation.ADD_INDEX
PROCEED = Disposition.PROCEED
MITIGATE = Disposition.PROCEED_WITH_MITIGATION
STOP = Disposition.DO_NOT_PROCEED
APPROVE, REJECT, RETURN = (
    ReviewDecision.APPROVE,
    ReviewDecision.REJECT,
    ReviewDecision.RETURN,
)

# id, raw_text, submitted_by, structured_change, [recommendations], [review_actions],
# reviewed, outcome, created_at, finalized_at
SCENARIOS = [
    (
        "demo-01",
        "Remove the column customer_legacy_id from the orders table",
        "bruno.tavares",
        _sc(DROP, "orders", "customer_legacy_id"),
        [_rec(
            1, MITIGATE,
            "A coluna `customer_legacy_id` é referenciada por duas views de relatório "
            "(`reporting.v_customer_orders`, `reporting.v_legacy_bridge`) e ainda é lida "
            "pelo serviço `cs_lookup` (~4 leituras/dia). A remoção é viável, mas só depois "
            "de migrar esses consumidores.",
            [
                "Refatorar `reporting.v_customer_orders` e `reporting.v_legacy_bridge` "
                "para não dependerem de `customer_legacy_id`.",
                "Combinar com o time do `cs_lookup` uma data de corte e um campo substituto.",
                "Aplicar a remoção em janela de baixo tráfego, com plano de rollback.",
            ],
        )],
        [ReviewAction(decision=APPROVE, reviewer="data.owner",
                      note="Views já migradas na sprint anterior; cs_lookup avisado.")],
        True, Outcome.APPROVED, "2026-06-17T09:12:00", "2026-06-17T15:40:00",
    ),
    (
        "demo-02",
        "drop column orders.notes_internal",
        "carla.menezes",
        _sc(DROP, "orders", "notes_internal"),
        [_rec(
            1, PROCEED,
            "`orders.notes_internal` não tem dependentes registrados nem uso a jusante. "
            "Remoção de baixo risco; pode seguir sem revisão humana.",
        )],
        [],
        False, Outcome.AUTO_FINALIZED, "2026-06-23T11:05:00", "2026-06-23T11:05:30",
    ),
    (
        "demo-03",
        "add index on orders(customer_id)",
        "diego.rocha",
        _sc(INDEX, "orders", index_columns=["customer_id"]),
        [_rec(
            1, PROCEED,
            "Índice em `orders(customer_id)`. O único consumidor listado "
            "(`ops_dashboard`, ~90 leituras/dia) está abaixo do limiar de contenção; "
            "criação padrão é segura. Ainda assim, use `CREATE INDEX CONCURRENTLY`.",
        )],
        [],
        False, Outcome.AUTO_FINALIZED, "2026-06-30T14:20:00", "2026-06-30T14:20:45",
    ),
    (
        "demo-04",
        "alter column orders.status set not null",
        "ana.lima",
        _sc(ALTER, "orders", "status", alter_detail="SET NOT NULL"),
        [_rec(
            1, MITIGATE,
            "`orders.status` alimenta a view `reporting.v_open_orders`. Tornar a coluna "
            "NOT NULL exige garantir que não há linhas nulas e que a carga que popula "
            "`status` nunca omite o campo.",
            [
                "Rodar `SELECT count(*) FROM orders WHERE status IS NULL` e corrigir os "
                "registros antes do ALTER.",
                "Adicionar a constraint com `NOT VALID` e depois `VALIDATE CONSTRAINT` "
                "para evitar lock longo.",
                "Revisar o job de ingestão para sempre preencher `status`.",
            ],
        )],
        [ReviewAction(decision=APPROVE, reviewer="paula.andrade",
                      note="Backfill concluído; 0 nulos. Aprovado com constraint NOT VALID.")],
        True, Outcome.APPROVED, "2026-07-03T10:30:00", "2026-07-04T09:15:00",
    ),
    (
        "demo-05",
        "remover a coluna orders.id",
        "felipe.souza",
        _sc(DROP, "orders", "id"),
        [_rec(
            1, STOP,
            "`orders.id` é a chave primária da tabela e é alvo da foreign key "
            "`fk_order_items_order`; o job `warehouse_sync` também a lê diariamente. "
            "Remover a coluna quebraria a integridade referencial e o pipeline do "
            "Data Warehouse. Não prosseguir.",
        )],
        [ReviewAction(decision=REJECT, reviewer="gustavo.nunes",
                      note="PK da tabela — pedido inviável. Rejeitado.")],
        True, Outcome.REJECTED, "2026-07-08T16:45:00", "2026-07-08T17:02:00",
    ),
    (
        "demo-06",
        "drop column orders.customer_id",
        "mariana.costa",
        _sc(DROP, "orders", "customer_id"),
        [
            _rec(
                1, MITIGATE,
                "`orders.customer_id` é lida ativamente pelo `ops_dashboard` "
                "(~90 leituras/dia). Sem dependências estruturais, mas o dashboard "
                "quebraria. Prosseguir só após ajustar o consumidor.",
                ["Atualizar as queries do `ops_dashboard` para não usar `customer_id`."],
            ),
            _rec(
                2, MITIGATE,
                "Revisão após devolução: o time do dashboard confirmou que `customer_id` "
                "pode ser derivado de `orders JOIN customers`. Plano de migração anexado.",
                [
                    "Publicar a nova versão do `ops_dashboard` sem `customer_id`.",
                    "Remover a coluna em D+7 após a publicação, com rollback pronto.",
                ],
                note="Anexar plano de migração do ops_dashboard antes de aprovar.",
            ),
        ],
        [
            ReviewAction(decision=RETURN, reviewer="paula.andrade",
                         note="Anexar plano de migração do ops_dashboard antes de aprovar."),
            ReviewAction(decision=APPROVE, reviewer="paula.andrade",
                         note="Plano recebido e revisado. Aprovado para D+7."),
        ],
        True, Outcome.APPROVED, "2026-07-14T08:50:00", "2026-07-16T13:20:00",
    ),
    (
        "demo-07",
        "criar índice em orders(status)",
        "rafael.dias",
        _sc(INDEX, "orders", index_columns=["status"]),
        [_rec(
            1, PROCEED,
            "Índice em `orders(status)`. Nenhum consumidor de leitura pesada listado "
            "para a coluna; a criação tem baixo raio de impacto. Usar "
            "`CREATE INDEX CONCURRENTLY` para não bloquear escritas.",
        )],
        [],
        False, Outcome.AUTO_FINALIZED, "2026-07-20T09:40:00", "2026-07-20T09:40:50",
    ),
    (
        "demo-08",
        "drop column orders.legacy_region",
        "juliana.pires",
        _sc(DROP, "orders", "legacy_region"),
        [_rec(
            1, STOP,
            "Não foi possível localizar `orders.legacy_region` na fonte de catálogo. "
            "Sem confirmar que a coluna existe e o que depende dela, qualquer remoção é "
            "cega. Não prosseguir até esclarecer o alvo.",
        )],
        [ReviewAction(decision=REJECT, reviewer="renata.barros",
                      note="Coluna não existe no catálogo atual. Pedido fechado.")],
        True, Outcome.REJECTED, "2026-07-24T15:10:00", "2026-07-24T15:33:00",
    ),
    (
        "demo-09",
        "alterar coluna orders.customer_legacy_id para varchar(64)",
        "thiago.gomes",
        _sc(ALTER, "orders", "customer_legacy_id", alter_detail="TYPE varchar(64)"),
        [_rec(
            1, MITIGATE,
            "Aumentar o tamanho de `customer_legacy_id` de varchar para varchar(64) é "
            "compatível para os dados atuais, mas as views `reporting.v_customer_orders` "
            "e `reporting.v_legacy_bridge` precisam ser recriadas e o `cs_lookup` "
            "revalidado contra o novo tipo.",
            [
                "Recriar as duas views de `reporting` após o ALTER.",
                "Rodar os testes de contrato do `cs_lookup` no ambiente de staging.",
            ],
        )],
        [ReviewAction(decision=APPROVE, reviewer="data.owner",
                      note="Alteração widening, sem perda. Aprovado.")],
        True, Outcome.APPROVED, "2026-07-29T11:25:00", "2026-07-29T18:05:00",
    ),
    (
        "demo-10",
        "drop column ghost_table.foo",
        "larissa.melo",
        _sc(DROP, "ghost_table", "foo"),
        [_rec(
            1, STOP,
            "A tabela `ghost_table` não foi encontrada na fonte de evidências. O pedido "
            "provavelmente se refere a um objeto que não existe (ou já foi removido). "
            "Não prosseguir.",
        )],
        [ReviewAction(decision=REJECT, reviewer="gustavo.nunes",
                      note="Tabela inexistente. Provável erro de digitação no nome.")],
        True, Outcome.REJECTED, "2026-08-03T09:00:00", "2026-08-03T09:12:00",
    ),
    (
        "demo-11",
        "add index on orders(customer_id, status)",
        "bruno.tavares",
        _sc(INDEX, "orders", index_columns=["customer_id", "status"]),
        [_rec(
            1, PROCEED,
            "Índice composto em `orders(customer_id, status)`. A coluna líder "
            "(`customer_id`) tem leitura moderada (`ops_dashboard`, ~90/dia), abaixo do "
            "limiar de contenção. Criar concorrentemente e monitorar o tamanho do índice.",
        )],
        [],
        False, Outcome.AUTO_FINALIZED, "2026-08-07T13:15:00", "2026-08-07T13:16:10",
    ),
    (
        "demo-12",
        "remove column orders.status",
        "carla.menezes",
        _sc(DROP, "orders", "status"),
        [
            _rec(
                1, MITIGATE,
                "`orders.status` é referenciada pela view `reporting.v_open_orders`. "
                "Não há uso recente de aplicação, mas a view precisa ser tratada antes "
                "da remoção.",
                ["Reescrever ou aposentar `reporting.v_open_orders`."],
            ),
            _rec(
                2, MITIGATE,
                "Após devolução: `reporting.v_open_orders` foi identificada como legada "
                "e sem consumidores ativos. Pode ser removida junto com a coluna.",
                [
                    "Dropar `reporting.v_open_orders` na mesma migração.",
                    "Comunicar a mudança no canal de governança de dados.",
                ],
                note="Confirmar se v_open_orders ainda é usada em algum relatório agendado.",
            ),
        ],
        [
            ReviewAction(decision=RETURN, reviewer="renata.barros",
                         note="Confirmar se v_open_orders ainda é usada em algum "
                              "relatório agendado."),
            ReviewAction(decision=APPROVE, reviewer="renata.barros",
                         note="Sem relatórios agendados. Aprovado, dropar view junto."),
        ],
        True, Outcome.APPROVED, "2026-08-11T10:05:00", "2026-08-13T16:30:00",
    ),
    (
        "demo-13",
        "alter column orders.notes_internal type text",
        "diego.rocha",
        _sc(ALTER, "orders", "notes_internal", alter_detail="TYPE text"),
        [_rec(
            1, PROCEED,
            "`orders.notes_internal` já é text e não tem dependentes nem uso a jusante. "
            "A alteração é efetivamente um no-op de baixo risco.",
        )],
        [],
        False, Outcome.AUTO_FINALIZED, "2026-08-18T09:30:00", "2026-08-18T09:30:20",
    ),
    (
        "demo-14",
        "drop column customers.ssn",
        "ana.lima",
        _sc(DROP, "customers", "ssn"),
        [_rec(
            1, STOP,
            "A coluna `customers.ssn` não aparece no catálogo deste ambiente. Como se "
            "trata de um campo potencialmente sensível, a remoção precisa de confirmação "
            "explícita do dono do dado e do time de privacidade antes de qualquer ação.",
        )],
        [ReviewAction(decision=REJECT, reviewer="renata.barros",
                      note="Fora do escopo do catálogo atual; encaminhado à privacidade.")],
        True, Outcome.REJECTED, "2026-08-22T14:00:00", "2026-08-22T14:25:00",
    ),
    (
        "demo-15",
        "alterar orders.id para bigint generated always as identity",
        "felipe.souza",
        _sc(ALTER, "orders", "id",
            alter_detail="TYPE bigint GENERATED ALWAYS AS IDENTITY"),
        [_rec(
            1, STOP,
            "`orders.id` é chave primária, é referenciada pela foreign key "
            "`fk_order_items_order` e é lida pelo job `warehouse_sync`. Trocar a coluna "
            "para IDENTITY reescreveria a PK e invalidaria as chaves estrangeiras "
            "existentes. Não prosseguir sem um plano de migração dedicado.",
        )],
        [ReviewAction(decision=REJECT, reviewer="gustavo.nunes",
                      note="Mudança em PK com FK dependente. Rejeitado nesta forma.")],
        True, Outcome.REJECTED, "2026-08-27T11:40:00", "2026-08-27T12:05:00",
    ),
]


def build_record(row) -> AnalysisRecord:
    (rid, raw, who, sc, recs, actions, reviewed, outcome, created, finalized) = row
    c, f = _dt(created), _dt(finalized)
    ev = _evidence(sc)
    risk = risk_rules.assess(sc, ev).model_copy(
        update={"pass_number": 1, "assessed_at": c + timedelta(seconds=8)}
    )
    if actions:
        span = (f - c) / len(actions)
        actions = [
            a.model_copy(update={"decided_at": c + span * (i + 1)})
            for i, a in enumerate(actions)
        ]
    return AnalysisRecord(
        id=rid,
        change_request=ChangeRequest(
            id=rid, raw_text=raw, submitted_by=who, submitted_at=c
        ),
        structured_change=sc,
        evidence=ev,
        risk_assessments=[risk],
        recommendations=recs,
        review_actions=actions,
        reviewed=reviewed,
        outcome=outcome,
        final_recommendation_version=recs[-1].version,
        step_log=_step_log(sc, risk, recs, actions, reviewed, outcome),
        created_at=_dt(created),
        finalized_at=_dt(finalized),
    )


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("set DATABASE_URL first")
    repo = PostgresRepository(url)
    repo.setup()
    for row in SCENARIOS:
        rec = build_record(row)
        repo.save(rec)
        print(f"{rec.id}  {rec.outcome.value:15}  {rec.risk_assessments[-1].category.value:6}"
              f"  {rec.change_request.raw_text[:56]}")
    print(f"\n{len(SCENARIOS)} rows upserted into analysis_record.")


if __name__ == "__main__":
    main()
