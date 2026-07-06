import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Text, Boolean, Integer, Float, JSON, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class DevelopmentPlanStatus(str, PyEnum):
    draft = "draft"
    reviewed = "reviewed"
    approved = "approved"
    active = "active"
    completed = "completed"


class CompletionStatus(str, PyEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    carried_forward = "carried_forward"


class SuggestionType(str, PyEnum):
    new_goal = "new_goal"
    new_indicator = "new_indicator"
    adjust_weight = "adjust_weight"
    raise_target = "raise_target"


class SuggestionStatus(str, PyEnum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    partially_adopted = "partially_adopted"


class ReviewReport(Base):
    __tablename__ = "review_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    final_result_id: Mapped[str] = mapped_column(String(36), ForeignKey("final_results.id"), nullable=False, unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)
    strengths_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    improvement_areas: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    development_suggestions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_by_user: Mapped[bool] = mapped_column(Boolean, default=False)
    user_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_cycle_focus_areas: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DevelopmentPlan(Base):
    __tablename__ = "development_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    review_report_id: Mapped[str] = mapped_column(String(36), ForeignKey("review_reports.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    plan_version: Mapped[int] = mapped_column(Integer, default=1)
    goals: Mapped[dict] = mapped_column(JSON, nullable=False)
    actions: Mapped[dict] = mapped_column(JSON, nullable=False)
    required_resources: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timeline: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    smart_evaluation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_suggestions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[DevelopmentPlanStatus] = mapped_column(Enum(DevelopmentPlanStatus), default=DevelopmentPlanStatus.draft)
    approved_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_status: Mapped[CompletionStatus] = mapped_column(Enum(CompletionStatus), default=CompletionStatus.not_started)
    completion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    carry_forward_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_to_next_cycle: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InheritanceSuggestion(Base):
    __tablename__ = "inheritance_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    previous_development_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("development_plans.id"), nullable=False, index=True)
    previous_final_result_id: Mapped[str] = mapped_column(String(36), ForeignKey("final_results.id"), nullable=False)
    new_period_id: Mapped[str] = mapped_column(String(36), ForeignKey("periods.id"), nullable=False, index=True)
    suggestion_type: Mapped[SuggestionType] = mapped_column(Enum(SuggestionType), nullable=False)
    suggestions: Mapped[dict] = mapped_column(JSON, nullable=False)
    adopted_goal_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("goals.id"), nullable=True)
    adopted_indicator_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("indicators.id"), nullable=True)
    adoption_modifications: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[SuggestionStatus] = mapped_column(Enum(SuggestionStatus), default=SuggestionStatus.pending)
    rejected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
