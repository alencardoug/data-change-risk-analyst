"""T037 / T052 — deterministic routing functions."""

from dcra.domain.enums import ReviewDecision, RiskCategory
from dcra.domain.models import ReviewAction, RiskAssessment
from dcra.graph.nodes import route_after_assess, route_after_recommend, route_after_review


def _risk(cat: RiskCategory) -> RiskAssessment:
    return RiskAssessment(category=cat, factors=[])


def test_route_after_assess():
    assert route_after_assess({"evidence_gap": True}) == "investigate"
    assert route_after_assess({"evidence_gap": False}) == "recommend"
    assert route_after_assess({}) == "recommend"


def test_route_after_recommend_low_finalizes():
    assert route_after_recommend({"risk": _risk(RiskCategory.LOW)}) == "finalize"


def test_route_after_recommend_medium_high_go_to_review():
    assert route_after_recommend({"risk": _risk(RiskCategory.MEDIUM)}) == "review"
    assert route_after_recommend({"risk": _risk(RiskCategory.HIGH)}) == "review"


def _action(decision: ReviewDecision, **kw) -> ReviewAction:
    return ReviewAction(decision=decision, reviewer="r", **kw)


def test_route_after_review_approve_reject_finalize():
    assert route_after_review({"review_actions": [_action(ReviewDecision.APPROVE)]}) == "finalize"
    assert route_after_review({"review_actions": [_action(ReviewDecision.REJECT)]}) == "finalize"
