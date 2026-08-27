"""T049 / S3 — RETURN marked 'evidence missing' re-runs evidence + risk (may change category)."""

from dcra.domain.enums import EvidenceKind, EvidenceStatus, Outcome, RiskCategory
from dcra.domain.models import EvidenceItem
from dcra.graph.build import build_graph, pending_interrupt, resume, run
from tests.conftest import InMemoryRepository, fake_investigate

# the "reviewer knew about" dependency the investigator surfaces on the reassess pass
_FK = EvidenceItem(
    kind=EvidenceKind.DEPENDENCY, key="fk_reviewer_flagged", status=EvidenceStatus.OBTAINED,
    source="lineage", payload={"dependent": "fk_reviewer_flagged", "dependent_type": "foreign_key"},
)


def test_evidence_missing_return_reassesses_and_bumps_risk(make_deps, change_request):
    repo = InMemoryRepository()
    deps = make_deps(repository=repo, investigate_fn=fake_investigate([_FK]))
    graph = build_graph(deps)
    cr = change_request("drop column orders.customer_legacy_id")

    first = pending_interrupt(run(graph, cr))
    assert first["risk"]["category"] == RiskCategory.MEDIUM.value
    assert first["revision_count"] == 0

    second = pending_interrupt(
        resume(graph, cr.id, {"decision": "RETURN", "reviewer": "owner",
                              "note": "an FK you missed references this", "evidence_missing": True})
    )
    assert second is not None
    assert second["risk"]["category"] == RiskCategory.HIGH.value  # re-assessment changed it
    assert second["recommendation"]["version"] == 2
    assert second["recommendation"]["prompted_by_note"]
    assert second["revision_count"] == 1

    out = resume(graph, cr.id, {"decision": "APPROVE", "reviewer": "owner"})
    assert out["outcome"] == Outcome.APPROVED
    rec = repo.saved[cr.id]
    # multiple risk passes recorded (FR-017 / SC-010)
    assert [ra.pass_number for ra in rec.risk_assessments][:2] == [1, 2]
    assert len(rec.recommendations) == 2
