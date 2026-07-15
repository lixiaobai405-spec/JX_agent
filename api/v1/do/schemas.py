import math
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictFloat, StrictInt, field_validator


# Goal and Indicator Schemas
class GoalResponse(BaseModel):
    id: str
    owner_user_id: str
    period_id: str
    title: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IndicatorResponse(BaseModel):
    id: str
    goal_id: str
    name: str
    definition: str | None
    direction: str
    weight: float
    target_value: float | None
    score_method: str
    redline: bool
    indicator_type: str | None = None
    unit: str | None = None
    target_display: str | None = None
    target_logic: str | None = None
    scoring_rule: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# Data Checkin Schemas
class QuantitativeCheckinValue(BaseModel):
    value_type: Literal["quantitative"]
    value: StrictInt | StrictFloat

    model_config = {"extra": "forbid"}

    @field_validator("value")
    @classmethod
    def value_must_be_finite(cls, value: int | float) -> int | float:
        if not math.isfinite(value):
            raise ValueError("quantitative value must be finite")
        return value


class QualitativeCheckinValue(BaseModel):
    value_type: Literal["qualitative"]
    value: Literal["not_started", "in_progress", "completed", "exceeded"]

    model_config = {"extra": "forbid"}


class RedlineCheckinValue(BaseModel):
    value_type: Literal["redline"]
    value: Annotated[StrictInt, Field(ge=0)]

    model_config = {"extra": "forbid"}


DataCheckinValue = Annotated[
    QuantitativeCheckinValue | QualitativeCheckinValue | RedlineCheckinValue,
    Field(discriminator="value_type"),
]


class DataCheckinCreate(BaseModel):
    indicator_id: str
    actual_value: DataCheckinValue
    progress_description: str | None = None
    issues: str | None = None

    model_config = {"extra": "forbid"}


class DataCheckinUpdate(BaseModel):
    actual_value: DataCheckinValue | None = None
    progress_description: str | None = None
    issues: str | None = None

    model_config = {"extra": "forbid"}


class DataCheckinResponse(BaseModel):
    id: str
    indicator_id: str
    user_id: str
    actual_value: dict
    progress_description: str | None
    issues: str | None
    submitted_at: datetime
    created_at: datetime | None

    model_config = {"from_attributes": True}


# Diagnostic Report Schemas
class DiagnosticReportGenerateRequest(BaseModel):
    goal_id: str
    feedback: str | None = None


class DiagnosticReportResponse(BaseModel):
    id: str
    goal_id: str
    user_id: str
    report_date: datetime
    overall_progress: float | None
    weighted_achievement_rate: float | None
    time_progress: float | None
    progress_deviation: float | None
    indicators_analysis: dict | None
    root_cause_analysis: dict | None
    improvement_suggestions: dict | None
    traffic_light_status: str | None
    generated_by_ai: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# Coaching Request Schemas
class CoachingRequestCreate(BaseModel):
    diagnostic_report_id: str
    request_reason: str | None = None
    urgency_level: str = "normal"


class CoachingRequestStatusUpdate(BaseModel):
    status: str
    response: str | None = None


class CoachingRequestResponse(BaseModel):
    id: str
    diagnostic_report_id: str
    goal_id: str | None = None
    requester_id: str
    manager_id: str
    request_reason: str | None
    urgency_level: str
    status: str
    scheduled_time: datetime | None
    actual_time: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

