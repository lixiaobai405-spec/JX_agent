from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, field_validator

from models.check_phase import FinalResultStatus
from models.do_phase import TrafficLightStatus
from models.period import PeriodStatus


class PeriodCreate(BaseModel):
    user_id: str | None = None
    name: str
    start_date: datetime
    end_date: datetime
    description: str | None = None

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: datetime, info) -> datetime:
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class PeriodUpdate(BaseModel):
    name: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class PeriodStatusUpdate(BaseModel):
    status: PeriodStatus


class PeriodResponse(BaseModel):
    id: str
    user_id: str
    name: str
    start_date: datetime
    end_date: datetime
    status: PeriodStatus
    d_phase_completed: bool = False
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PeriodListResponse(BaseModel):
    items: list[PeriodResponse]
    total: int
    page: int
    page_size: int


class DiagnosticSummary(BaseModel):
    id: str
    report_date: date
    weighted_achievement_rate: float | None
    traffic_light_status: TrafficLightStatus | None


class FinalResultSummary(BaseModel):
    id: str
    final_grade: str
    status: FinalResultStatus
    confirmed_at: datetime


class PeriodHistoryItem(BaseModel):
    period_id: str
    user_id: str
    name: str
    start_date: datetime
    end_date: datetime
    status: PeriodStatus
    description: str | None
    goal_id: str | None
    diagnostic_summary: DiagnosticSummary | None
    final_result_summary: FinalResultSummary | None
    has_data_conflict: bool


class PeriodHistoryResponse(BaseModel):
    items: list[PeriodHistoryItem]
    total: int
    page: int
    page_size: int
