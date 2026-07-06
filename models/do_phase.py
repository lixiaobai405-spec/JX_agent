import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class PeriodType(str, PyEnum):
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"


class TrafficLightStatus(str, PyEnum):
    green = "green"
    yellow = "yellow"
    red = "red"


class UrgencyLevel(str, PyEnum):
    low = "low"
    normal = "normal"
    high = "high"


class CoachingRequestStatus(str, PyEnum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    completed = "completed"


class DataCheckin(Base):
    __tablename__ = "data_checkins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    indicator_id: Mapped[str] = mapped_column(String(36), ForeignKey("indicators.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    actual_value: Mapped[dict] = mapped_column(JSON, nullable=False)
    progress_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    issues: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DiagnosticReport(Base):
    __tablename__ = "diagnostic_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    goal_id: Mapped[str] = mapped_column(String(36), ForeignKey("goals.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    report_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    overall_progress: Mapped[float | None] = mapped_column(Float, nullable=True)
    weighted_achievement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_progress: Mapped[float | None] = mapped_column(Float, nullable=True)
    progress_deviation: Mapped[float | None] = mapped_column(Float, nullable=True)
    indicators_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    root_cause_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    improvement_suggestions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    traffic_light_status: Mapped[TrafficLightStatus | None] = mapped_column(Enum(TrafficLightStatus), nullable=True)
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CoachingRequest(Base):
    __tablename__ = "coaching_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    diagnostic_report_id: Mapped[str] = mapped_column(String(36), ForeignKey("diagnostic_reports.id"), nullable=False, index=True)
    requester_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    manager_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    request_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    urgency_level: Mapped[UrgencyLevel] = mapped_column(Enum(UrgencyLevel), default=UrgencyLevel.normal)
    status: Mapped[CoachingRequestStatus] = mapped_column(Enum(CoachingRequestStatus), default=CoachingRequestStatus.pending)
    scheduled_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

