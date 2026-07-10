from api.v1.plan.service import _indicator_score_method
from models.check_phase import ScoreMethod


def test_indicator_score_method_preserves_qualitative_and_redline_types():
    assert _indicator_score_method({"type": "positive"}) == ScoreMethod.ratio
    assert _indicator_score_method({"type": "negative"}) == ScoreMethod.ratio
    assert _indicator_score_method({"type": "qualitative"}) == ScoreMethod.manual
    assert _indicator_score_method({"type": "redline"}) == ScoreMethod.binary
