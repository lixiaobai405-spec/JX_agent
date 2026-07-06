import math
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    EmailExistsError,
    PermissionDeniedError,
    UserAccessDeniedError,
    UserDeleteDeniedError,
    UserModifyDeniedError,
    UserNotFoundError,
    UsernameExistsError,
)
from core.security import get_password_hash
from models.organization import Department, Position
from models.token import RefreshToken
from models.user import User, UserRole, UserStatus


def _can_access(current_user: User, target_id: str, subordinate_ids: list[str]) -> bool:
    if current_user.role in (UserRole.hr_admin, UserRole.system_admin):
        return True
    if current_user.id == target_id:
        return True
    if current_user.role == UserRole.manager and target_id in subordinate_ids:
        return True
    return False


async def _get_subordinate_ids(db: AsyncSession, manager_id: str) -> list[str]:
    """BFS traversal to get all subordinate user IDs."""
    ids = []
    queue = [manager_id]
    while queue:
        current = queue.pop(0)
        result = await db.execute(
            select(User.id).where(
                and_(User.manager_id == current, User.status == UserStatus.active)
            )
        )
        children = result.scalars().all()
        ids.extend(children)
        queue.extend(children)
    return ids


async def _enrich_user(db: AsyncSession, user: User) -> dict:
    dept_name = None
    if user.department_id:
        dept = await db.get(Department, user.department_id)
        dept_name = dept.name if dept else None

    pos_name = None
    if user.position_id:
        pos = await db.get(Position, user.position_id)
        pos_name = pos.title if pos else None

    manager_name = None
    if user.manager_id:
        mgr = await db.get(User, user.manager_id)
        manager_name = mgr.full_name if mgr else None

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "status": user.status.value,
        "department_id": user.department_id,
        "department_name": dept_name,
        "position_id": user.position_id,
        "position_name": pos_name,
        "manager_id": user.manager_id,
        "manager_name": manager_name,
        "hire_date": user.hire_date,
        "phone": user.phone,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login_at": user.last_login_at,
    }


async def list_users(
    db: AsyncSession,
    current_user: User,
    page: int = 1,
    limit: int = 20,
    role: str | None = None,
    department_id: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> dict:
    limit = min(limit, 100)
    query = select(User).where(User.deleted_at.is_(None))

    if current_user.role == UserRole.employee:
        query = query.where(User.id == current_user.id)
    elif current_user.role == UserRole.manager:
        sub_ids = await _get_subordinate_ids(db, current_user.id)
        allowed = [current_user.id] + sub_ids
        query = query.where(User.id.in_(allowed))

    if role:
        query = query.where(User.role == role)
    if department_id:
        query = query.where(User.department_id == department_id)
    if status:
        query = query.where(User.status == status)
    if search:
        like = f"%{search}%"
        query = query.where(or_(
            User.username.ilike(like),
            User.full_name.ilike(like),
            User.email.ilike(like),
        ))

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()
    pages = math.ceil(total / limit) if total else 1

    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    users = result.scalars().all()

    data = [await _enrich_user(db, u) for u in users]
    return {"total": total, "page": page, "limit": limit, "pages": pages, "data": data}


async def get_user(db: AsyncSession, current_user: User, user_id: str) -> dict:
    sub_ids = await _get_subordinate_ids(db, current_user.id) if current_user.role == UserRole.manager else []
    if not _can_access(current_user, user_id, sub_ids):
        raise UserAccessDeniedError()

    user = await db.get(User, user_id)
    if not user or user.deleted_at:
        raise UserNotFoundError()
    return await _enrich_user(db, user)


async def create_user(db: AsyncSession, data: dict) -> dict:
    # Check uniqueness
    existing = await db.execute(select(User).where(User.username == data["username"]))
    if existing.scalar_one_or_none():
        raise UsernameExistsError()

    existing = await db.execute(select(User).where(User.email == data["email"]))
    if existing.scalar_one_or_none():
        raise EmailExistsError()

    role_str = data.get("role", "employee")
    role = UserRole(role_str) if isinstance(role_str, str) else role_str

    user = User(
        username=data["username"],
        email=data["email"],
        full_name=data["full_name"],
        hashed_password=get_password_hash(data["password"]),
        role=role,
        department_id=data.get("department_id"),
        position_id=data.get("position_id"),
        manager_id=data.get("manager_id"),
        hire_date=data.get("hire_date"),
        phone=data.get("phone"),
    )
    db.add(user)
    await db.flush()
    return await _enrich_user(db, user)


async def update_user(db: AsyncSession, current_user: User, user_id: str, data: dict) -> dict:
    user = await db.get(User, user_id)
    if not user or user.deleted_at:
        raise UserNotFoundError()

    is_admin = current_user.role in (UserRole.hr_admin, UserRole.system_admin)
    is_self = current_user.id == user_id
    sub_ids = await _get_subordinate_ids(db, current_user.id) if current_user.role == UserRole.manager else []
    is_sub = user_id in sub_ids

    if not (is_admin or is_self or is_sub):
        raise UserModifyDeniedError()

    # Employees can only update email and phone
    allowed_fields = {"email", "full_name", "phone", "department_id", "position_id", "manager_id", "role", "status"}
    if not is_admin:
        allowed_fields = {"email", "phone"} if is_self else {"email", "phone", "department_id", "position_id", "manager_id"}

    for field in allowed_fields:
        if field in data and data[field] is not None:
            if field == "email":
                existing = await db.execute(select(User).where(and_(User.email == data[field], User.id != user_id)))
                if existing.scalar_one_or_none():
                    raise EmailExistsError()
            setattr(user, field, data[field])

    await db.flush()
    await db.refresh(user)
    return await _enrich_user(db, user)


async def delete_user(db: AsyncSession, current_user: User, user_id: str) -> None:
    if current_user.role != UserRole.system_admin:
        raise UserDeleteDeniedError()

    user = await db.get(User, user_id)
    if not user or user.deleted_at:
        raise UserNotFoundError()

    user.status = UserStatus.inactive
    user.deleted_at = datetime.now(timezone.utc)

    # Revoke all sessions
    result = await db.execute(
        select(RefreshToken).where(
            and_(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        )
    )
    for rt in result.scalars().all():
        rt.revoked_at = datetime.now(timezone.utc)
    await db.flush()


async def get_subordinates(
    db: AsyncSession, current_user: User, user_id: str, direct_only: bool = False
) -> dict:
    # Permission check
    sub_ids_of_current = await _get_subordinate_ids(db, current_user.id) if current_user.role == UserRole.manager else []
    is_admin = current_user.role in (UserRole.hr_admin, UserRole.system_admin)
    if not (is_admin or current_user.id == user_id or user_id in sub_ids_of_current):
        raise UserAccessDeniedError()

    user = await db.get(User, user_id)
    if not user:
        raise UserNotFoundError()

    if direct_only:
        result = await db.execute(
            select(User).where(and_(User.manager_id == user_id, User.status == UserStatus.active))
        )
        subs = result.scalars().all()
        items = []
        for u in subs:
            dept_name = None
            pos_name = None
            if u.department_id:
                d = await db.get(Department, u.department_id)
                dept_name = d.name if d else None
            if u.position_id:
                p = await db.get(Position, u.position_id)
                pos_name = p.title if p else None
            items.append({
                "id": u.id, "username": u.username, "full_name": u.full_name,
                "role": u.role.value, "department_name": dept_name,
                "position_name": pos_name, "is_direct": True, "level": 1,
            })
        return {"user_id": user_id, "user_name": user.full_name, "subordinates": items, "total": len(items)}

    # BFS with level tracking
    items = []
    queue = [(user_id, 0)]
    visited = {user_id}
    while queue:
        parent_id, depth = queue.pop(0)
        result = await db.execute(
            select(User).where(and_(User.manager_id == parent_id, User.status == UserStatus.active))
        )
        for u in result.scalars().all():
            if u.id in visited:
                continue
            visited.add(u.id)
            dept_name = None
            pos_name = None
            if u.department_id:
                d = await db.get(Department, u.department_id)
                dept_name = d.name if d else None
            if u.position_id:
                p = await db.get(Position, u.position_id)
                pos_name = p.title if p else None
            items.append({
                "id": u.id, "username": u.username, "full_name": u.full_name,
                "role": u.role.value, "department_name": dept_name,
                "position_name": pos_name, "is_direct": depth == 0, "level": depth + 1,
            })
            queue.append((u.id, depth + 1))

    return {"user_id": user_id, "user_name": user.full_name, "subordinates": items, "total": len(items)}


async def get_my_team(db: AsyncSession, current_user: User) -> dict:
    sub_ids = await _get_subordinate_ids(db, current_user.id)
    members = []
    for sid in sub_ids:
        u = await db.get(User, sid)
        if u:
            members.append({
                "id": u.id, "username": u.username, "full_name": u.full_name,
                "role": u.role.value, "is_direct": u.manager_id == current_user.id,
            })
    return {
        "manager": {
            "id": current_user.id, "username": current_user.username,
            "full_name": current_user.full_name, "role": current_user.role.value,
        },
        "team_members": members,
        "total_members": len(members),
    }
