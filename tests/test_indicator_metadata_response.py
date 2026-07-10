from datetime import datetime, timezone
from types import SimpleNamespace

from api.v1.do.service import build_indicator_response
from models.check_phase import IndicatorDirection, ScoreMethod


def test_indicator_response_preserves_contract_metadata():
    indicator = SimpleNamespace(
        id="indicator-1",
        goal_id="goal-1",
        name="区域净销售额",
        definition="华东区便利系统当月实际开票销售额",
        direction=IndicatorDirection.positive,
        weight=0.45,
        target_value=800,
        score_method=ScoreMethod.ratio,
        redline=False,
        created_at=datetime(2026, 7, 10, tzinfo=timezone.utc),
    )

    response = build_indicator_response(
        indicator,
        {
            "name": "区域净销售额",
            "type": "positive",
            "unit": "万元",
            "target_display": "800万元",
            "target_logic": "自上而下（年度目标分解）",
            "scoring_rule": "(实际/目标)*100%",
        },
    )

    assert response["indicator_type"] == "positive"
    assert response["unit"] == "万元"
    assert response["target_display"] == "800万元"
    assert response["target_logic"] == "自上而下（年度目标分解）"
    assert response["scoring_rule"] == "(实际/目标)*100%"
    assert response["weight"] == 0.45


def test_indicator_response_falls_back_without_contract_metadata():
    indicator = SimpleNamespace(
        id="indicator-2",
        goal_id="goal-1",
        name="重大安全事故",
        definition=None,
        direction=IndicatorDirection.negative,
        weight=0,
        target_value=0,
        score_method=ScoreMethod.ratio,
        redline=True,
        created_at=datetime(2026, 7, 10, tzinfo=timezone.utc),
    )

    response = build_indicator_response(indicator)

    assert response["indicator_type"] == "redline"
    assert response["target_display"] == "0"
    assert response["scoring_rule"] is None
