from datetime import datetime
from pydantic import BaseModel, field_validator

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
    description: str | None = None


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
