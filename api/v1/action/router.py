from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.action import schemas, service
from core.database import get_db
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/action", tags=["action"])


# Review Reports
@router.post("/review-reports/generate", response_model=schemas.ReviewReportResponse)
async def generate_review_report(
    data: schemas.ReviewReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.generate_review_report(db, current_user, data.final_result_id)


@router.get("/review-reports/{report_id}", response_model=schemas.ReviewReportResponse)
async def get_review_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_review_report(db, current_user, report_id)


@router.put("/review-reports/{report_id}/feedback", response_model=schemas.ReviewReportResponse)
async def submit_user_feedback(
    report_id: str,
    data: schemas.ReviewReportFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.submit_user_feedback(db, current_user, report_id, data.user_feedback)


@router.get("/review-reports/user/{user_id}/period/{period_id}", response_model=schemas.ReviewReportResponse | None)
async def get_user_period_report(
    user_id: str,
    period_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_user_period_report(db, current_user, user_id, period_id)


# Development Plans
@router.post("/development-plans", response_model=schemas.DevelopmentPlanResponse)
async def create_development_plan(
    data: schemas.DevelopmentPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.create_development_plan(db, current_user, data.review_report_id, data.goals, data.actions, data.required_resources, data.timeline)


@router.get("/development-plans/my-plans", response_model=list[schemas.DevelopmentPlanResponse])
async def list_my_plans(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.list_my_plans(db, current_user)


@router.get("/development-plans/my-team", response_model=list[schemas.DevelopmentPlanResponse])
async def list_team_plans(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.list_team_plans(db, current_user)


@router.get("/development-plans/{plan_id}", response_model=schemas.DevelopmentPlanResponse)
async def get_development_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_development_plan(db, current_user, plan_id)


@router.put("/development-plans/{plan_id}", response_model=schemas.DevelopmentPlanResponse)
async def update_development_plan(
    plan_id: str,
    data: schemas.DevelopmentPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.update_development_plan(db, current_user, plan_id, data.dict(exclude_unset=True))


@router.post("/development-plans/{plan_id}/ai-review", response_model=schemas.DevelopmentPlanResponse)
async def ai_review_plan(
    plan_id: str,
    data: schemas.PlanAIReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.ai_review_plan(db, current_user, plan_id, data.feedback)


@router.post("/development-plans/{plan_id}/submit", response_model=schemas.DevelopmentPlanResponse)
async def submit_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.submit_plan(db, current_user, plan_id)


@router.post("/development-plans/{plan_id}/approve", response_model=schemas.DevelopmentPlanResponse)
async def approve_plan(
    plan_id: str,
    data: schemas.PlanApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.approve_plan(db, current_user, plan_id, data.approved, data.comment)


# Inheritance Suggestions
@router.post("/inheritance-suggestions/generate", response_model=schemas.InheritanceSuggestionResponse)
async def generate_inheritance_suggestions(
    data: schemas.InheritanceSuggestionGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.generate_inheritance_suggestions(db, current_user, data.user_id, data.from_period_id, data.to_period_id)


@router.get("/inheritance-suggestions/{suggestion_id}", response_model=schemas.InheritanceSuggestionResponse)
async def get_inheritance_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_inheritance_suggestion(db, current_user, suggestion_id)


@router.post("/inheritance-suggestions/{suggestion_id}/accept", response_model=schemas.InheritanceSuggestionResponse)
async def accept_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.accept_suggestion(db, current_user, suggestion_id)


@router.post("/inheritance-suggestions/{suggestion_id}/reject", response_model=schemas.InheritanceSuggestionResponse)
async def reject_suggestion(
    suggestion_id: str,
    data: schemas.SuggestionRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.reject_suggestion(db, current_user, suggestion_id, data.reason)


@router.get("/inheritance-suggestions/user/{user_id}/period/{period_id}", response_model=list[schemas.InheritanceSuggestionResponse])
async def get_user_period_suggestions(
    user_id: str,
    period_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_user_period_suggestions(db, current_user, user_id, period_id)
