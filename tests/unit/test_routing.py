"""T037 — deterministic routing functions."""

from dcra.domain.enums import RiskCategory
from dcra.domain.models import RiskAssessment
from dcra.graph.nodes import route_after_assess, route_after_recommend


def _risk(cat: RiskCategory) -> RiskAssessment:
    return RiskAssessment(category=cat, factors=[])


def test_route_after_assess():
    assert route_after_assess({"evidence_gap": True}) == "investigate"
    assert route_after_assess({"evidence_gap": False}) == "recommend"
    assert route_after_assess({}) == "recommend"


def test_route_after_recommend_low_finalizes():
    assert route_after_recommend({"risk": _risk(RiskCategory.LOW)}) == "finalize"


def test_route_after_recommend_medium_high_stop_in_us1():
    assert route_after_recommend({"risk": _risk(RiskCategory.MEDIUM)}) == "stop"
    assert route_after_recommend({"risk": _risk(RiskCategory.HIGH)}) == "stop"
