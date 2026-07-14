from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints


class JobAnalysisCreate(BaseModel):
    user_id: str
    jd_text: str


class JobAnalysisResponse(BaseModel):
    id: str
    user_id: str
    jd_text: str
    job_prototype_code: str | None
    quantifiability_score: int | None
    output_cycle_score: int | None
    work_nature_score: int | None
    features: dict | None
    confidence: float | None
    analysis_result: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ContractGenerateRequest(BaseModel):
    period_id: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
    ]
    user_id: str
    job_analysis_id: str
    feedback: str | None = None


class ContractConfirmRequest(BaseModel):
    confirmed_by: str


class ContractResponse(BaseModel):
    id: str
    goal_id: str | None
    job_prototype_code: str
    strategy_config: dict
    contract_data: dict
    ai_generated: bool
    confirmed_at: datetime | None
    confirmed_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateResponse(BaseModel):
    id: str
    job_prototype_code: str
    name: str
    definition: str | None
    direction: str
    recommended_weight: float | None
    score_method: str
    template_data: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PrototypeResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    indicator_count_min: int
    indicator_count_max: int
    quantitative_ratio_min: float
    quantitative_ratio_max: float

    model_config = {"from_attributes": True}


class PrototypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    indicator_count_min: int | None = None
    indicator_count_max: int | None = None
    quantitative_ratio_min: float | None = None
    quantitative_ratio_max: float | None = None
