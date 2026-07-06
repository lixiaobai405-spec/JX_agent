from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.users import schemas, service
from core.database import get_db
from core.dependencies import get_current_active_user, require_roles

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/team", response_model=schemas.TeamResponse)
async def get_my_team(
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_my_team(db=db, current_user=current_user)


@router.get("/", response_model=schemas.UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: str | None = None,
    department_id: str | None = None,
    status: str | None = None,
    search: str | None = None,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_users(
        db=db, current_user=current_user,
        page=page, limit=limit, role=role,
        department_id=department_id, status=status, search=search,
    )


@router.post("/", status_code=201)
async def create_user(
    body: schemas.UserCreate,
    _=Depends(require_roles("hr_admin", "system_admin")),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_user(db=db, data=body.model_dump())


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_user(db=db, current_user=current_user, user_id=user_id)


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    body: schemas.UserUpdate,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_user(
        db=db, current_user=current_user, user_id=user_id,
        data=body.model_dump(exclude_none=True),
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_user(db=db, current_user=current_user, user_id=user_id)
    return {"message": "User deleted successfully"}


@router.get("/{user_id}/subordinates", response_model=schemas.SubordinatesResponse)
async def get_subordinates(
    user_id: str,
    direct_only: bool = Query(False),
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_subordinates(
        db=db, current_user=current_user,
        user_id=user_id, direct_only=direct_only,
    )
