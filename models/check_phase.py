import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class IndicatorDirection(str, PyEnum):
    positive = "positive"
    negative = "negative"


class ScoreMethod(str, PyEnum):
    ratio = "ratio"
    mapping = "mapping"
    binary = "binary"
    manual = "manual"


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    period_id: Mapped[str] = mapped_column(String(36), ForeignKey("periods.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    performance_contract_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("performance_contracts.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Indicator(Base):
    __tablename__ = "indicators"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    goal_id: Mapped[str] = mapped_column(String(36), ForeignKey("goals.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    direction: Mapped[IndicatorDirection] = mapped_column(Enum(IndicatorDirection), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_method: Mapped[ScoreMethod] = mapped_column(Enum(ScoreMethod), nullable=False)
    redline: Mapped[bool] = mapped_column(Boolean, default=False)
    is_team_indicator: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    template_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("indicator_templates.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SelfAssessmentStatus(str, PyEnum):
    draft = "draft"
    submitted = "submitted"
    withdrawn = "withdrawn"


class SelfAssessment(Base):
    __tablename__ = "self_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    goal_id: Mapped[str] = mapped_column(String(36), ForeignKey("goals.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    items: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[SelfAssessmentStatus] = mapped_column(Enum(SelfAssessmentStatus), default=SelfAssessmentStatus.draft)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvaluationTaskStatus(str, PyEnum):
    pending = "pending"
    completed = "completed"
    expired = "expired"


class EvaluationTask(Base):
    __tablename__ = "evaluation_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    goal_id: Mapped[str] = mapped_column(String(36), ForeignKey("goals.id"), nullable=False, index=True)
    indicator_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("indicators.id"), nullable=True)
    evaluator_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    assigned_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    status: Mapped[EvaluationTaskStatus] = mapped_column(Enum(EvaluationTaskStatus), default=EvaluationTaskStatus.pending)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_tasks.id"), nullable=False, index=True)
    goal_id: Mapped[str] = mapped_column(String(36), ForeignKey("goals.id"), nullable=False, index=True)
    indicator_id: Mapped[str] = mapped_column(String(36), ForeignKey("indicators.id"), nullable=False, index=True)
    evaluator_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScoreAggregate(Base):
    __tablename__ = "score_aggregates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    goal_id: Mapped[str] = mapped_column(String(36), ForeignKey("goals.id"), nullable=False, unique=True, index=True)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GradeMode(str, PyEnum):
    absolute = "absolute"
    relative = "relative"


class GradeRule(Base):
    __tablename__ = "grade_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    period_id: Mapped[str] = mapped_column(String(36), ForeignKey("periods.id"), nullable=False, index=True)
    mode: Mapped[GradeMode] = mapped_column(Enum(GradeMode), nullable=False)
    absolute_bands: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    relative_distribution: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fallback_strategy: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FinalResultStatus(str, PyEnum):
    pending = "pending"
    confirmed = "confirmed"
    adjusted = "adjusted"
    archived = "archived"


class FinalResult(Base):
    __tablename__ = "final_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    goal_id: Mapped[str] = mapped_column(String(36), ForeignKey("goals.id"), nullable=False, unique=True, index=True)
    computed_score_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("score_aggregates.id"), nullable=True)
    suggested_grade: Mapped[str | None] = mapped_column(String(10), nullable=True)
    final_grade: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    confirmed_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    adjustment_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[FinalResultStatus] = mapped_column(Enum(FinalResultStatus), default=FinalResultStatus.pending)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
