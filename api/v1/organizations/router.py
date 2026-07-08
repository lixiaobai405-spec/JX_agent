from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.organizations import schemas, service
from core.database import get_db
from core.dependencies import get_current_active_user, require_roles

router = APIRouter(prefix="/organizations", tags=["organizations"])

_read_auth = Depends(get_current_active_user)
_write_auth = Depends(require_roles("hr_admin", "system_admin"))
_admin_auth = Depends(require_roles("system_admin"))


# ─── Departments ─────────────────────────────────────────────────────────────

@router.get("/departments", response_model=schemas.DepartmentListResponse)
async def list_departments(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    parent_id: str | None = None,
    search: str | None = None,
    _=_read_auth,
    db: AsyncSession = Depends(get_db),
):
    return await service.list_departments(db=db, page=page, limit=limit, parent_id=parent_id, search=search)


@router.post("/departments", status_code=201, response_model=schemas.DepartmentResponse)
async def create_department(
    body: schemas.DepartmentCreate,
    _=_write_auth,
    db: AsyncSession = Depends(get_db),
):
    return await service.create_department(db=db, data=body.model_dump())


@router.get("/departments/{dept_id}", response_model=schemas.DepartmentResponse)
async def get_department(dept_id: str, _=_read_auth, db: AsyncSession = Depends(get_db)):
    return await service.get_department(db=db, dept_id=dept_id)


@router.put("/departments/{dept_id}", response_model=schemas.DepartmentResponse)
async def update_department(
    dept_id: str, body: schemas.DepartmentUpdate,
    _=_write_auth, db: AsyncSession = Depends(get_db),
):
    return await service.update_department(db=db, dept_id=dept_id, data=body.model_dump(exclude_unset=True))


@router.delete("/departments/{dept_id}")
async def delete_department(dept_id: str, _=_admin_auth, db: AsyncSession = Depends(get_db)):
    await service.delete_department(db=db, dept_id=dept_id)
    return {"message": "Department deleted successfully"}


@router.get("/departments/{dept_id}/tree", response_model=schemas.DepartmentTreeNode)
async def get_department_tree(dept_id: str, _=_read_auth, db: AsyncSession = Depends(get_db)):
    return await service.get_department_tree(db=db, dept_id=dept_id)


@router.get("/departments/{dept_id}/members", response_model=schemas.DepartmentMembersResponse)
async def get_department_members(
    dept_id: str,
    include_subdepts: bool = Query(False),
    _=_read_auth,
    db: AsyncSession = Depends(get_db),
):
    return await service.get_department_members(db=db, dept_id=dept_id, include_subdepts=include_subdepts)


# ─── Positions ───────────────────────────────────────────────────────────────

@router.get("/positions", response_model=schemas.PositionListResponse)
async def list_positions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    department_id: str | None = None,
    search: str | None = None,
    _=_read_auth,
    db: AsyncSession = Depends(get_db),
):
    return await service.list_positions(db=db, page=page, limit=limit, department_id=department_id, search=search)


@router.post("/positions", status_code=201, response_model=schemas.PositionResponse)
async def create_position(
    body: schemas.PositionCreate, _=_write_auth, db: AsyncSession = Depends(get_db),
):
    return await service.create_position(db=db, data=body.model_dump())


@router.get("/positions/{pos_id}", response_model=schemas.PositionResponse)
async def get_position(pos_id: str, _=_read_auth, db: AsyncSession = Depends(get_db)):
    return await service.get_position(db=db, pos_id=pos_id)


@router.put("/positions/{pos_id}", response_model=schemas.PositionResponse)
async def update_position(
    pos_id: str, body: schemas.PositionUpdate,
    _=_write_auth, db: AsyncSession = Depends(get_db),
):
    return await service.update_position(db=db, pos_id=pos_id, data=body.model_dump(exclude_none=True))


@router.delete("/positions/{pos_id}")
async def delete_position(pos_id: str, _=_admin_auth, db: AsyncSession = Depends(get_db)):
    await service.delete_position(db=db, pos_id=pos_id)
    return {"message": "Position deleted successfully"}
