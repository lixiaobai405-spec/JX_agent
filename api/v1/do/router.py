from fastapi import APIRouter, Depends, Query, Body
from models.user import UserRole
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.do import schemas, service
from core.database import get_db
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/do", tags=["do"])


# Goals and Indicators
@router.get("/goals/current", response_model=schemas.GoalResponse | None)
async def get_current_goal(
    period_id: str,
    user_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    target_id = current_user.id
    if user_id and current_user.role in (UserRole.manager, UserRole.hr_admin, UserRole.system_admin):
        target_id = user_id
    return await service.get_goal_by_user(db, target_id, period_id)


@router.get("/goals/{goal_id}/indicators", response_model=list[schemas.IndicatorResponse])
async def list_goal_indicators(
    goal_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.list_goal_indicators(db, goal_id)


# Data Checkins
@router.post("/checkins", response_model=schemas.DataCheckinResponse)
async def submit_checkin(
    data: schemas.DataCheckinCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.submit_checkin(db, current_user, data.indicator_id, data.actual_value, data.progress_description, data.issues)


@router.get("/checkins/{checkin_id}", response_model=schemas.DataCheckinResponse)
async def get_checkin(
    checkin_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_checkin(db, checkin_id)


@router.put("/checkins/{checkin_id}", response_model=schemas.DataCheckinResponse)
async def update_checkin(
    checkin_id: str,
    data: schemas.DataCheckinUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.update_checkin(db, checkin_id, data.actual_value, data.progress_description, data.issues)


@router.get("/checkins/indicator/{indicator_id}", response_model=list[schemas.DataCheckinResponse])
async def list_indicator_checkins(
    indicator_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.list_indicator_checkins(db, indicator_id)


# Diagnostic Reports
@router.post("/diagnostic-reports/generate", response_model=schemas.DiagnosticReportResponse)
async def generate_diagnostic_report(
    data: schemas.DiagnosticReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.generate_diagnostic_report(db, current_user, data.goal_id, data.feedback)


@router.get("/diagnostic-reports/{report_id}", response_model=schemas.DiagnosticReportResponse)
async def get_diagnostic_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_diagnostic_report(db, report_id)


@router.get("/diagnostic-reports/goal/{goal_id}", response_model=list[schemas.DiagnosticReportResponse])
async def list_goal_reports(
    goal_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.list_goal_reports(db, goal_id)


@router.get("/diagnostic-reports/goal/{goal_id}/latest", response_model=schemas.DiagnosticReportResponse | None)
async def get_latest_report(
    goal_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_latest_report(db, goal_id)


# Coaching Requests
@router.post("/coaching-requests", response_model=schemas.CoachingRequestResponse)
async def create_coaching_request(
    data: schemas.CoachingRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.create_coaching_request(db, current_user, data.diagnostic_report_id, data.request_reason, data.urgency_level)


@router.get("/coaching-requests/my-requests", response_model=list[schemas.CoachingRequestResponse])
async def list_my_requests(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.list_my_requests(db, current_user)


@router.get("/coaching-requests/my-team", response_model=list[schemas.CoachingRequestResponse])
async def list_team_requests(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.list_team_requests(db, current_user)


@router.get("/coaching-requests/{request_id}", response_model=schemas.CoachingRequestResponse)
async def get_coaching_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_coaching_request(db, request_id)


@router.put("/coaching-requests/{request_id}/status", response_model=schemas.CoachingRequestResponse)
async def update_request_status(
    request_id: str,
    data: schemas.CoachingRequestStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.update_request_status(db, request_id, data.status, data.response)



