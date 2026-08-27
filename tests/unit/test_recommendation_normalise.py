"""T062 — recommendation post-processing (contracts/llm-schemas.md §Call 2):
the node forces version / ai_generated / confidence and repairs an invalid mitigation state."""

from dcra.domain.enums import Confidence, Disposition
from dcra.domain.models import Recommendation
from dcra.llm.factory import _normalise_rec


def test_forces_version_and_ai_flag():
    raw = Recommendation(version=1, disposition=Disposition.PROCEED, rationale="ok")
    out = _normalise_rec(raw, version=3, note="a note", reduced=False)
    assert out.version == 3
    assert out.ai_generated is True
    assert out.prompted_by_note == "a note"
    assert out.confidence == Confidence.NORMAL


def test_reduced_confidence_is_forced_when_evidence_unavailable():
    raw = Recommendation(disposition=Disposition.PROCEED, rationale="ok", confidence=Confidence.NORMAL)
    out = _normalise_rec(raw, version=1, note=None, reduced=True)
    assert out.confidence == Confidence.REDUCED


def test_proceed_with_mitigation_but_no_mitigations_is_downgraded():
    # a model returning PROCEED_WITH_MITIGATION with an empty list would fail validation;
    # _normalise_rec repairs it to DO_NOT_PROCEED with a logged note.
    raw = Recommendation.model_construct(
        version=1, disposition=Disposition.PROCEED_WITH_MITIGATION, rationale="do it",
        mitigations=[], confidence=Confidence.NORMAL, prompted_by_note=None, ai_generated=True,
    )
    out = _normalise_rec(raw, version=1, note=None, reduced=False)
    assert out.disposition == Disposition.DO_NOT_PROCEED
    assert "mitigations were unspecified" in out.rationale
