from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.periods import schemas, service
from core.database import get_db
from core.dependencies import get_current_active_user
from models.period import PeriodStatus

router = APIRouter(prefix="/periods", tags=["periods"])


@router.post("/", response_model=schemas.PeriodResponse)
async def create_period(
    data: schemas.PeriodCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    period = await service.create_period(db, current_user, data.model_dump())
    return period


@router.get("/", response_model=schemas.PeriodListResponse)
async def list_periods(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: PeriodStatus | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.list_periods(db, current_user, page, limit, status)


@router.get("/current", response_model=schemas.PeriodResponse | None)
async def get_current_period(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_current_period(db, current_user.id)


@router.get("/history", response_model=schemas.PeriodHistoryResponse)
async def list_period_history(
    user_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.list_period_history(
        db=db,
        current_user=current_user,
        user_id=user_id,
        page=page,
        limit=limit,
    )


@router.get("/{period_id}", response_model=schemas.PeriodResponse)
async def get_period(
    period_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_period(db, period_id)


@router.put("/{period_id}", response_model=schemas.PeriodResponse)
async def update_period(
    period_id: str,
    data: schemas.PeriodUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.update_period(db, current_user, period_id, data.model_dump(exclude_unset=True))


@router.put("/{period_id}/status", response_model=schemas.PeriodResponse)
async def update_period_status(
    period_id: str,
    data: schemas.PeriodStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.update_period_status(db, current_user, period_id, data.status)


@router.post("/{period_id}/complete-d-phase", response_model=schemas.PeriodResponse)
async def complete_d_phase(
    period_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.complete_d_phase(db, current_user, period_id)


@router.delete("/{period_id}")
async def delete_period(
    period_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    await service.delete_period(db, current_user, period_id)
    return {"message": "Period deleted successfully"}

