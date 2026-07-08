import pytest
from pydantic import ValidationError

from api.v1.check.schemas import EvaluationCreate, SelfAssessmentCreate, SelfAssessmentUpdate
from api.v1.check.service import validate_score_items


def test_self_assessment_create_rejects_score_above_100():
    with pytest.raises(ValidationError):
        SelfAssessmentCreate(
            goal_id="goal-1",
            items={"indicator-1": {"score": 101, "comment": "too high"}},
        )


def test_self_assessment_create_rejects_score_below_0():
    with pytest.raises(ValidationError):
        SelfAssessmentCreate(
            goal_id="goal-1",
            items={"indicator-1": {"score": -1, "comment": "too low"}},
        )


def test_self_assessment_update_allows_valid_scores():
    payload = SelfAssessmentUpdate(items={"indicator-1": {"score": 88, "comment": "ok"}})
    assert payload.items["indicator-1"]["score"] == 88


def test_evaluation_create_rejects_score_above_100():
    with pytest.raises(ValidationError):
        EvaluationCreate(task_id="task-1", indicator_id="indicator-1", score=6666)


def test_evaluation_create_rejects_score_below_0():
    with pytest.raises(ValidationError):
        EvaluationCreate(task_id="task-1", indicator_id="indicator-1", score=-1)


def test_service_validation_rejects_invalid_items_when_called_directly():
    with pytest.raises(ValueError, match="评分必须在 0-100 之间"):
        validate_score_items({"indicator-1": {"score": 626662}})
