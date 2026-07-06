import math

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    DepartmentCodeExistsError,
    DepartmentHasChildrenError,
    DepartmentHasMembersError,
    DepartmentNotFoundError,
    PositionCodeExistsError,
    PositionHasMembersError,
    PositionNotFoundError,
)
from models.organization import Department, Position
from models.user import User


# ─── Departments ────────────────────────────────────────────────────────────

async def _dept_member_count(db: AsyncSession, dept_id: str) -> int:
    result = await db.execute(
        select(func.count(User.id)).where(
            and_(User.department_id == dept_id, User.deleted_at.is_(None))
        )
    )
    return result.scalar_one()


async def _dept_to_dict(db: AsyncSession, dept: Department) -> dict:
    manager_name = None
    if dept.manager_id:
        mgr = await db.get(User, dept.manager_id)
        manager_name = mgr.full_name if mgr else None
    count = await _dept_member_count(db, dept.id)
    return {
        "id": dept.id, "name": dept.name, "code": dept.code,
        "parent_id": dept.parent_id, "level": dept.level,
        "manager_id": dept.manager_id, "manager_name": manager_name,
        "description": dept.description, "member_count": count,
        "created_at": dept.created_at,
    }


async def list_departments(
    db: AsyncSession, page: int = 1, limit: int = 20,
    parent_id: str | None = None, search: str | None = None,
) -> dict:
    limit = min(limit, 100)
    query = select(Department).where(Department.deleted_at.is_(None))
    if parent_id:
        query = query.where(Department.parent_id == parent_id)
    if search:
        query = query.where(Department.name.ilike(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    depts = (await db.execute(query.offset((page - 1) * limit).limit(limit))).scalars().all()
    data = [await _dept_to_dict(db, d) for d in depts]
    return {"total": total, "page": page, "limit": limit, "data": data}


async def get_department(db: AsyncSession, dept_id: str) -> dict:
    dept = await db.get(Department, dept_id)
    if not dept or dept.deleted_at:
        raise DepartmentNotFoundError()
    return await _dept_to_dict(db, dept)


async def create_department(db: AsyncSession, data: dict) -> dict:
    existing = await db.execute(select(Department).where(Department.code == data["code"]))
    if existing.scalar_one_or_none():
        raise DepartmentCodeExistsError()

    level = 1
    path = "/"
    if data.get("parent_id"):
        parent = await db.get(Department, data["parent_id"])
        if parent:
            level = parent.level + 1
            path = parent.path + parent.id + "/"

    dept = Department(
        name=data["name"], code=data["code"],
        parent_id=data.get("parent_id"), manager_id=data.get("manager_id"),
        description=data.get("description"), level=level, path=path,
    )
    db.add(dept)
    await db.flush()
    return await _dept_to_dict(db, dept)


async def update_department(db: AsyncSession, dept_id: str, data: dict) -> dict:
    dept = await db.get(Department, dept_id)
    if not dept or dept.deleted_at:
        raise DepartmentNotFoundError()
    for field in ("name", "manager_id", "description"):
        if field in data and data[field] is not None:
            setattr(dept, field, data[field])
    await db.flush()
    return await _dept_to_dict(db, dept)


async def delete_department(db: AsyncSession, dept_id: str) -> None:
    dept = await db.get(Department, dept_id)
    if not dept or dept.deleted_at:
        raise DepartmentNotFoundError()

    child_count = (await db.execute(
        select(func.count(Department.id)).where(
            and_(Department.parent_id == dept_id, Department.deleted_at.is_(None))
        )
    )).scalar_one()
    if child_count > 0:
        raise DepartmentHasChildrenError()

    member_count = await _dept_member_count(db, dept_id)
    if member_count > 0:
        raise DepartmentHasMembersError()

    from datetime import datetime, timezone
    dept.deleted_at = datetime.now(timezone.utc)
    await db.flush()


async def get_department_tree(db: AsyncSession, dept_id: str) -> dict:
    root = await db.get(Department, dept_id)
    if not root or root.deleted_at:
        raise DepartmentNotFoundError()

    async def build_tree(d: Department) -> dict:
        result = await db.execute(
            select(Department).where(
                and_(Department.parent_id == d.id, Department.deleted_at.is_(None))
            )
        )
        children = result.scalars().all()
        return {
            "id": d.id, "name": d.name, "level": d.level,
            "children": [await build_tree(c) for c in children],
        }

    return await build_tree(root)


async def get_department_members(
    db: AsyncSession, dept_id: str, include_subdepts: bool = False
) -> dict:
    dept = await db.get(Department, dept_id)
    if not dept or dept.deleted_at:
        raise DepartmentNotFoundError()

    if include_subdepts:
        dept_ids = [dept_id]
        queue = [dept_id]
        while queue:
            parent = queue.pop(0)
            result = await db.execute(
                select(Department.id).where(
                    and_(Department.parent_id == parent, Department.deleted_at.is_(None))
                )
            )
            children = result.scalars().all()
            dept_ids.extend(children)
            queue.extend(children)
        query = select(User).where(
            and_(User.department_id.in_(dept_ids), User.deleted_at.is_(None))
        )
    else:
        query = select(User).where(
            and_(User.department_id == dept_id, User.deleted_at.is_(None))
        )

    users = (await db.execute(query)).scalars().all()
    members = []
    for u in users:
        pos_name = None
        if u.position_id:
            p = await db.get(Position, u.position_id)
            pos_name = p.title if p else None
        members.append({
            "id": u.id, "username": u.username, "full_name": u.full_name,
            "position_name": pos_name,
        })
    return {
        "department_id": dept_id, "department_name": dept.name,
        "members": members, "total": len(members),
    }


# ─── Positions ──────────────────────────────────────────────────────────────

async def _pos_member_count(db: AsyncSession, pos_id: str) -> int:
    result = await db.execute(
        select(func.count(User.id)).where(
            and_(User.position_id == pos_id, User.deleted_at.is_(None))
        )
    )
    return result.scalar_one()


async def _pos_to_dict(db: AsyncSession, pos: Position) -> dict:
    dept_name = None
    if pos.department_id:
        dept = await db.get(Department, pos.department_id)
        dept_name = dept.name if dept else None
    count = await _pos_member_count(db, pos.id)
    return {
        "id": pos.id, "name": pos.title, "code": pos.code,
        "level": pos.job_level, "department_id": pos.department_id,
        "department_name": dept_name, "description": pos.description,
        "member_count": count, "created_at": pos.created_at,
    }


async def list_positions(
    db: AsyncSession, page: int = 1, limit: int = 20,
    department_id: str | None = None, search: str | None = None,
) -> dict:
    limit = min(limit, 100)
    query = select(Position).where(Position.deleted_at.is_(None))
    if department_id:
        query = query.where(Position.department_id == department_id)
    if search:
        query = query.where(Position.title.ilike(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    positions = (await db.execute(query.offset((page - 1) * limit).limit(limit))).scalars().all()
    data = [await _pos_to_dict(db, p) for p in positions]
    return {"total": total, "page": page, "limit": limit, "data": data}


async def get_position(db: AsyncSession, pos_id: str) -> dict:
    pos = await db.get(Position, pos_id)
    if not pos or pos.deleted_at:
        raise PositionNotFoundError()
    return await _pos_to_dict(db, pos)


async def create_position(db: AsyncSession, data: dict) -> dict:
    existing = await db.execute(select(Position).where(Position.code == data["code"]))
    if existing.scalar_one_or_none():
        raise PositionCodeExistsError()

    pos = Position(
        title=data["name"], code=data["code"],
        department_id=data.get("department_id"), job_level=data.get("level"),
        description=data.get("description"),
    )
    db.add(pos)
    await db.flush()
    return await _pos_to_dict(db, pos)


async def update_position(db: AsyncSession, pos_id: str, data: dict) -> dict:
    pos = await db.get(Position, pos_id)
    if not pos or pos.deleted_at:
        raise PositionNotFoundError()
    if "name" in data and data["name"]:
        pos.title = data["name"]
    if "level" in data:
        pos.job_level = data["level"]
    if "department_id" in data:
        pos.department_id = data["department_id"]
    if "description" in data:
        pos.description = data["description"]
    await db.flush()
    return await _pos_to_dict(db, pos)


async def delete_position(db: AsyncSession, pos_id: str) -> None:
    pos = await db.get(Position, pos_id)
    if not pos or pos.deleted_at:
        raise PositionNotFoundError()

    count = await _pos_member_count(db, pos_id)
    if count > 0:
        raise PositionHasMembersError()

    from datetime import datetime, timezone
    pos.deleted_at = datetime.now(timezone.utc)
    await db.flush()
