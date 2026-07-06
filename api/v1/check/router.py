from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.check import schemas, service
from core.database import get_db
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/check", tags=["check"])


# Self Assessment
@router.post("/self-assessments", response_model=schemas.SelfAssessmentResponse)
async def create_self_assessment(
    data: schemas.SelfAssessmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.create_self_assessment(db, current_user, data.goal_id, data.items)


@router.get("/self-assessments/{assessment_id}", response_model=schemas.SelfAssessmentResponse)
async def get_self_assessment(
    assessment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_self_assessment(db, assessment_id)


@router.put("/self-assessments/{assessment_id}", response_model=schemas.SelfAssessmentResponse)
async def update_self_assessment(
    assessment_id: str,
    data: schemas.SelfAssessmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.update_self_assessment(db, assessment_id, data.items)


@router.post("/self-assessments/{assessment_id}/submit", response_model=schemas.SelfAssessmentResponse)
async def submit_self_assessment(
    assessment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.submit_self_assessment(db, assessment_id)


@router.get("/self-assessments/goal/{goal_id}", response_model=schemas.SelfAssessmentResponse | None)
async def get_goal_self_assessment(
    goal_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_goal_self_assessment(db, goal_id)


# Evaluation Tasks
@router.get("/evaluation-tasks/my-pending", response_model=list[schemas.EvaluationTaskResponse])
async def get_my_pending_evaluation_tasks(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_my_pending_evaluation_tasks(db, current_user)


@router.post("/evaluation-tasks/generate", response_model=list[schemas.EvaluationTaskResponse])
async def generate_evaluation_tasks(
    data: schemas.EvaluationTaskGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.generate_evaluation_tasks(db, current_user, data.goal_id)


@router.get("/evaluation-tasks", response_model=list[schemas.EvaluationTaskResponse])
async def list_evaluation_tasks(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.list_evaluation_tasks(db, current_user, status)


# Evaluations
@router.post("/evaluations", response_model=schemas.EvaluationResponse)
async def submit_evaluation(
    data: schemas.EvaluationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.submit_evaluation(db, current_user, data.task_id, data.indicator_id, data.score, data.comment)


@router.get("/evaluations/goal/{goal_id}", response_model=list[schemas.EvaluationResponse])
async def list_goal_evaluations(
    goal_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.list_goal_evaluations(db, goal_id)


# Final Results
@router.post("/final-results/generate", response_model=schemas.FinalResultResponse)
async def generate_final_result(
    data: schemas.FinalResultGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.generate_final_result(db, current_user, data.goal_id)


@router.get("/final-results/goal/{goal_id}", response_model=schemas.FinalResultResponse | None)
async def get_final_result_by_goal(
    goal_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_final_result_by_goal(db, goal_id)


@router.put("/final-results/{result_id}/confirm", response_model=schemas.FinalResultResponse)
async def confirm_final_result(
    result_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.confirm_final_result(db, result_id, current_user)


@router.put("/final-results/{result_id}/adjust", response_model=schemas.FinalResultResponse)
async def adjust_final_result(
    result_id: str,
    data: schemas.FinalResultAdjust,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.adjust_final_result(db, result_id, data.final_grade, data.adjustment_reason, current_user)


