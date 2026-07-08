from datetime import datetime
from pydantic import BaseModel, Field


# Self Assessment
class SelfAssessmentItem(BaseModel):
    score: float = Field(ge=0, le=100)
    comment: str | None = None

    def __getitem__(self, key: str):
        return getattr(self, key)


class SelfAssessmentCreate(BaseModel):
    goal_id: str
    items: dict[str, SelfAssessmentItem]


class SelfAssessmentUpdate(BaseModel):
    items: dict[str, SelfAssessmentItem] | None = None


class SelfAssessmentResponse(BaseModel):
    id: str
    goal_id: str
    user_id: str
    items: dict
    status: str
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Evaluation Task
class EvaluationTaskGenerateRequest(BaseModel):
    goal_id: str


class EvaluationTaskResponse(BaseModel):
    id: str
    goal_id: str
    indicator_id: str | None
    evaluator_user_id: str
    assigned_by: str
    status: str
    assigned_at: datetime
    due_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# Evaluation
class EvaluationCreate(BaseModel):
    task_id: str
    indicator_id: str
    score: float = Field(ge=0, le=100)
    comment: str | None = None


class EvaluationResponse(BaseModel):
    id: str
    task_id: str
    goal_id: str
    indicator_id: str
    evaluator_id: str
    score: float
    comment: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# Score Aggregate
class ScoreAggregateResponse(BaseModel):
    id: str
    goal_id: str
    final_score: float
    breakdown: dict
    computed_at: datetime

    class Config:
        from_attributes = True


# Final Result
class FinalResultGenerateRequest(BaseModel):
    goal_id: str


class FinalResultResponse(BaseModel):
    id: str
    goal_id: str
    computed_score_id: str | None
    suggested_grade: str | None
    final_grade: str
    confirmed_by: str
    confirmed_at: datetime
    adjustment_reason: str | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FinalResultConfirm(BaseModel):
    pass


class FinalResultAdjust(BaseModel):
    final_grade: str
    adjustment_reason: str
