from datetime import datetime
from pydantic import BaseModel


# Review Report Schemas
class ReviewReportGenerateRequest(BaseModel):
    final_result_id: str


class ReviewReportResponse(BaseModel):
    id: str
    final_result_id: str
    user_id: str
    report_type: str
    strengths_analysis: dict | None
    improvement_areas: dict | None
    development_suggestions: dict | None
    ai_generated: bool
    generated_at: datetime
    reviewed_by_user: bool
    user_feedback: str | None
    next_cycle_focus_areas: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewReportFeedbackRequest(BaseModel):
    user_feedback: str


# Development Plan Schemas
class PlanAIReviewRequest(BaseModel):
    feedback: str | None = None


class DevelopmentPlanCreate(BaseModel):
    review_report_id: str
    goals: dict
    actions: dict
    required_resources: dict | None = None
    timeline: dict | None = None


class DevelopmentPlanUpdate(BaseModel):
    goals: dict | None = None
    actions: dict | None = None
    required_resources: dict | None = None
    timeline: dict | None = None


class DevelopmentPlanResponse(BaseModel):
    id: str
    review_report_id: str
    user_id: str
    plan_version: int
    goals: dict
    actions: dict
    required_resources: dict | None
    timeline: dict | None
    smart_evaluation: dict | None
    ai_reviewed: bool
    ai_suggestions: dict | None
    status: str
    approved_by: str | None
    approved_at: datetime | None
    completion_status: str
    completion_rate: float | None
    carry_forward_reason: str | None
    linked_to_next_cycle: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PlanApprovalRequest(BaseModel):
    approved: bool
    comment: str | None = None


# Inheritance Suggestion Schemas
class InheritanceSuggestionGenerateRequest(BaseModel):
    user_id: str
    from_period_id: str
    to_period_id: str


class InheritanceSuggestionResponse(BaseModel):
    id: str
    user_id: str
    previous_development_plan_id: str
    previous_final_result_id: str
    new_period_id: str
    suggestion_type: str
    suggestions: dict
    adopted_goal_id: str | None
    adopted_indicator_id: str | None
    adoption_modifications: dict | None
    status: str
    rejected_reason: str | None
    accepted_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SuggestionRejectRequest(BaseModel):
    reason: str
