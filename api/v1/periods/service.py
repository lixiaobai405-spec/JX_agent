from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import UserAccessDeniedError, UserNotFoundError
from models.check_phase import FinalResult, Goal
from models.do_phase import DiagnosticReport
from models.period import Period, PeriodStatus
from models.user import User, UserRole, UserStatus


STATUS_FLOW = {
    PeriodStatus.draft: [PeriodStatus.open],
    PeriodStatus.open: [PeriodStatus.closed],
    PeriodStatus.closed: [PeriodStatus.open, PeriodStatus.archived],
    PeriodStatus.archived: [PeriodStatus.closed],
}


async def _get_subordinate_ids(db: AsyncSession, manager_id: str) -> list[str]:
    direct_reports = (
        select(User.id.label("id"))
        .where(
            User.manager_id == manager_id,
            User.status == UserStatus.active,
            User.deleted_at.is_(None),
        )
        .cte("subordinate_ids", recursive=True)
    )
    descendants = (
        select(User.id.label("id"))
        .join(direct_reports, User.manager_id == direct_reports.c.id)
        .where(
            User.status == UserStatus.active,
            User.deleted_at.is_(None),
        )
    )
    subordinate_ids = direct_reports.union_all(descendants)
    result = await db.execute(select(subordinate_ids.c.id))
    return list(result.scalars().all())


async def create_period(db: AsyncSession, current_user: User, data: dict) -> Period:
    from core.exceptions import PermissionDeniedError

    if current_user.role not in (UserRole.manager, UserRole.hr_admin, UserRole.system_admin):
        raise PermissionDeniedError("Only managers and admins can create periods")

    # 如果没有指定 user_id，默认为当前用户
    if not data.get("user_id"):
        data["user_id"] = current_user.id

    # Manager 只能为自己或下属创建周期
    if current_user.role == UserRole.manager:
        subordinate_ids = await _get_subordinate_ids(db, current_user.id)
        subordinate_ids.append(current_user.id)
        if data["user_id"] not in subordinate_ids:
            raise PermissionDeniedError("Managers can only create periods for themselves or their subordinates")

    period = Period(**data)
    db.add(period)
    await db.commit()
    await db.refresh(period)
    return period


async def list_periods(
    db: AsyncSession,
    current_user: User,
    page: int = 1,
    limit: int = 20,
    status: PeriodStatus | None = None
) -> dict:
    limit = min(limit, 100)
    query = select(Period).where(Period.deleted_at.is_(None))

    if status:
        query = query.where(Period.status == status)
    else:
        query = query.where(Period.status != PeriodStatus.archived)

    # 根据角色过滤周期
    if current_user.role == UserRole.employee:
        query = query.where(Period.user_id == current_user.id)
    elif current_user.role == UserRole.manager:
        subordinate_ids = await _get_subordinate_ids(db, current_user.id)
        subordinate_ids.append(current_user.id)
        query = query.where(Period.user_id.in_(subordinate_ids))
    # HR/系统管理员：查询所有周期

    query = query.order_by(Period.start_date.desc())

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    periods = result.scalars().all()

    return {
        "items": periods,
        "total": total,
        "page": page,
        "page_size": limit
    }


async def list_period_history(
    db: AsyncSession,
    current_user: User,
    user_id: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict:
    target_user_id = current_user.id if user_id is None else user_id

    if target_user_id != current_user.id and current_user.role not in (
        UserRole.hr_admin,
        UserRole.system_admin,
    ):
        if current_user.role != UserRole.manager:
            raise UserAccessDeniedError()
        subordinate_ids = await _get_subordinate_ids(db, current_user.id)
        if target_user_id not in subordinate_ids:
            raise UserAccessDeniedError()

    target_result = await db.execute(
        select(User.id).where(
            User.id == target_user_id,
            User.deleted_at.is_(None),
        )
    )
    if target_result.scalar_one_or_none() is None:
        raise UserNotFoundError()

    page = max(page, 1)
    limit = max(1, min(limit, 100))
    period_filters = (
        Period.user_id == target_user_id,
        Period.status.in_((PeriodStatus.closed, PeriodStatus.archived)),
        Period.deleted_at.is_(None),
    )

    count_result = await db.execute(
        select(func.count()).select_from(Period).where(*period_filters)
    )
    total = count_result.scalar_one()

    period_result = await db.execute(
        select(Period)
        .where(*period_filters)
        .order_by(Period.end_date.desc(), Period.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    periods = period_result.scalars().all()
    period_ids = [period.id for period in periods]

    goal_result = await db.execute(
        select(Goal)
        .where(
            Goal.period_id.in_(period_ids),
            Goal.owner_user_id == target_user_id,
            Goal.deleted_at.is_(None),
        )
        .order_by(Goal.period_id, Goal.id)
    )
    goals_by_period: dict[str, list[Goal]] = {}
    for goal in goal_result.scalars().all():
        goals_by_period.setdefault(goal.period_id, []).append(goal)

    goal_by_period = {
        period_id: goals[0]
        for period_id, goals in goals_by_period.items()
        if len(goals) == 1
    }
    goal_ids = [goal.id for goal in goal_by_period.values()]

    diagnostic_result = await db.execute(
        select(DiagnosticReport)
        .where(
            DiagnosticReport.goal_id.in_(goal_ids),
            DiagnosticReport.user_id == target_user_id,
        )
        .order_by(
            DiagnosticReport.goal_id,
            DiagnosticReport.created_at.desc(),
            DiagnosticReport.id.desc(),
        )
    )
    latest_diagnostic_by_goal: dict[str, DiagnosticReport] = {}
    for diagnostic in diagnostic_result.scalars().all():
        latest_diagnostic_by_goal.setdefault(diagnostic.goal_id, diagnostic)

    final_result = await db.execute(
        select(FinalResult)
        .where(
            FinalResult.goal_id.in_(goal_ids),
            FinalResult.deleted_at.is_(None),
        )
        .order_by(
            FinalResult.goal_id,
            FinalResult.confirmed_at.desc(),
            FinalResult.id.desc(),
        )
    )
    final_result_by_goal: dict[str, FinalResult] = {}
    for result in final_result.scalars().all():
        final_result_by_goal.setdefault(result.goal_id, result)

    items = []
    for period in periods:
        period_goals = goals_by_period.get(period.id, [])
        has_data_conflict = len(period_goals) > 1
        goal = goal_by_period.get(period.id)
        diagnostic = latest_diagnostic_by_goal.get(goal.id) if goal else None
        result = final_result_by_goal.get(goal.id) if goal else None

        items.append({
            "period_id": period.id,
            "user_id": period.user_id,
            "name": period.name,
            "start_date": period.start_date,
            "end_date": period.end_date,
            "status": period.status,
            "description": period.description,
            "goal_id": goal.id if goal else None,
            "diagnostic_summary": {
                "id": diagnostic.id,
                "report_date": diagnostic.report_date,
                "weighted_achievement_rate": diagnostic.weighted_achievement_rate,
                "traffic_light_status": diagnostic.traffic_light_status,
            } if diagnostic else None,
            "final_result_summary": {
                "id": result.id,
                "final_grade": result.final_grade,
                "status": result.status,
                "confirmed_at": result.confirmed_at,
            } if result else None,
            "has_data_conflict": has_data_conflict,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": limit,
    }


async def get_period(db: AsyncSession, period_id: str) -> Period:
    from core.exceptions import PeriodNotFoundError

    period = await db.get(Period, period_id)
    if not period or period.deleted_at:
        raise PeriodNotFoundError()
    return period


async def get_current_period(db: AsyncSession, user_id: str) -> Period | None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Period).where(
            and_(
                Period.user_id == user_id,
                Period.status == PeriodStatus.open,
                Period.start_date <= now,
                Period.end_date >= now,
                Period.deleted_at.is_(None)
            )
        ).order_by(Period.created_at.desc())
    )
    return result.scalars().first()


async def update_period(db: AsyncSession, current_user: User, period_id: str, data: dict) -> Period:
    from core.exceptions import PermissionDeniedError

    if current_user.role not in (UserRole.manager, UserRole.hr_admin, UserRole.system_admin):
        raise PermissionDeniedError("Only managers and admins can update periods")

    period = await get_period(db, period_id)

    for key, value in data.items():
        if value is not None:
            setattr(period, key, value)

    await db.commit()
    await db.refresh(period)
    return period


async def update_period_status(db: AsyncSession, current_user: User, period_id: str, new_status: PeriodStatus) -> Period:
    from core.exceptions import PermissionDeniedError, PeriodStatusTransitionError, PeriodDateConflictError

    if current_user.role not in (UserRole.manager, UserRole.system_admin):
        raise PermissionDeniedError("Only managers and system admins can change period status")

    period = await get_period(db, period_id)

    # Managers can only change periods belonging to themselves or their subordinates.
    if current_user.role == UserRole.manager:
        subordinate_ids = await _get_subordinate_ids(db, current_user.id)
        allowed_ids = subordinate_ids + [current_user.id]
        if period.user_id not in allowed_ids:
            raise PermissionDeniedError("Managers can only change periods for themselves or their subordinates")

    if new_status not in STATUS_FLOW.get(period.status, []):
        raise PeriodStatusTransitionError(f"Cannot transition from {period.status.value} to {new_status.value}")

    if new_status == PeriodStatus.open:
        existing = await db.execute(
            select(Period).where(
                and_(Period.user_id == period.user_id, Period.status == PeriodStatus.open, Period.id != period_id, Period.deleted_at.is_(None))
            )
        )
        if existing.scalars().first():
            raise PeriodDateConflictError("Another period is already open for this user")

    period.status = new_status
    await db.commit()
    await db.refresh(period)
    return period


async def complete_d_phase(db: AsyncSession, current_user: User, period_id: str) -> Period:
    from core.exceptions import PermissionDeniedError

    if current_user.role not in (UserRole.manager, UserRole.hr_admin, UserRole.system_admin):
        raise PermissionDeniedError("Only managers and admins can complete D phase")

    period = await get_period(db, period_id)

    # Managers can only complete D phase for their subordinates
    if current_user.role == UserRole.manager:
        subordinate_ids = await _get_subordinate_ids(db, current_user.id)
        if period.user_id not in subordinate_ids:
            raise PermissionDeniedError("Managers can only complete D phase for their subordinates")

    period.d_phase_completed = True
    await db.commit()
    await db.refresh(period)
    return period


async def delete_period(db: AsyncSession, current_user: User, period_id: str) -> None:
    from core.exceptions import PermissionDeniedError, PeriodDeleteDeniedError

    if current_user.role != UserRole.system_admin:
        raise PermissionDeniedError("Only system admins can delete periods")

    period = await get_period(db, period_id)

    if period.status != PeriodStatus.draft:
        raise PeriodDeleteDeniedError("Only draft periods can be deleted")

    period.deleted_at = datetime.now(timezone.utc)
    await db.commit()
