import pytest
from pydantic import ValidationError

from api.v1.plan.schemas import ContractGenerateRequest
from api.v1.plan.service import _indicator_score_method
from models.check_phase import ScoreMethod


def test_indicator_score_method_preserves_qualitative_and_redline_types():
    assert _indicator_score_method({"type": "positive"}) == ScoreMethod.ratio
    assert _indicator_score_method({"type": "negative"}) == ScoreMethod.ratio
    assert _indicator_score_method({"type": "qualitative"}) == ScoreMethod.manual
    assert _indicator_score_method({"type": "redline"}) == ScoreMethod.binary


def test_contract_generate_request_rejects_empty_period_id():
    with pytest.raises(ValidationError):
        ContractGenerateRequest(
            period_id="",
            user_id="user-1",
            job_analysis_id="analysis-1",
        )
