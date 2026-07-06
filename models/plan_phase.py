import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class JobPrototype(Base):
    __tablename__ = "job_prototypes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(1), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantifiability_min: Mapped[int] = mapped_column(Integer, default=0)
    quantifiability_max: Mapped[int] = mapped_column(Integer, default=10)
    output_cycle_min: Mapped[int] = mapped_column(Integer, default=0)
    output_cycle_max: Mapped[int] = mapped_column(Integer, default=10)
    work_nature_min: Mapped[int] = mapped_column(Integer, default=0)
    work_nature_max: Mapped[int] = mapped_column(Integer, default=10)
    indicator_count_min: Mapped[int] = mapped_column(Integer, nullable=False)
    indicator_count_max: Mapped[int] = mapped_column(Integer, nullable=False)
    quantitative_ratio_min: Mapped[float] = mapped_column(Float, nullable=False)
    quantitative_ratio_max: Mapped[float] = mapped_column(Float, nullable=False)
    primary_target_setting: Mapped[str] = mapped_column(String(50), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class StrategyMatrix(Base):
    __tablename__ = "strategy_matrices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_prototype_code: Mapped[str] = mapped_column(String(1), ForeignKey("job_prototypes.code"), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(50), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class JobAnalysis(Base):
    __tablename__ = "job_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    job_prototype_code: Mapped[str | None] = mapped_column(String(1), ForeignKey("job_prototypes.code"), nullable=True, index=True)
    quantifiability_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_cycle_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    work_nature_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PerformanceContract(Base):
    __tablename__ = "performance_contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    goal_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    job_prototype_code: Mapped[str] = mapped_column(String(1), ForeignKey("job_prototypes.code"), nullable=False)
    strategy_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    contract_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    generation_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IndicatorTemplate(Base):
    __tablename__ = "indicator_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_prototype_code: Mapped[str] = mapped_column(String(1), ForeignKey("job_prototypes.code"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    recommended_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_method: Mapped[str] = mapped_column(String(20), nullable=False)
    template_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AIGenerationLog(Base):
    __tablename__ = "ai_generation_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    job_analysis_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("job_analyses.id"), nullable=True)
    model_used: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
