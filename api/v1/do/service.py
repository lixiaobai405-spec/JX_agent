from datetime import datetime, timezone, date

from pydantic import BaseModel, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.do.schemas import DataCheckinValue
from core.exceptions import AppException, PermissionDeniedError
from models.do_phase import DataCheckin, DiagnosticReport, CoachingRequest
from models.check_phase import Goal, Indicator
from models.plan_phase import PerformanceContract
from models.user import User, UserRole, UserStatus
from models.period import Period, PeriodStatus
from utils.text_formatting import normalize_markdown_text


_CHECKIN_VALUE_ADAPTER = TypeAdapter(DataCheckinValue)
_ADMIN_ROLES = (UserRole.hr_admin, UserRole.system_admin)


def _enum_value(value):
    return getattr(value, "value", value)


def _format_number(value: float | int | None) -> str | None:
    if value is None:
        return None
    return f"{value:g}"


def _contract_indicator_index(contract_data: dict | None) -> dict[str, dict]:
    indicators = (contract_data or {}).get("indicators", [])
    by_name: dict[str, list[dict]] = {}
    for item in indicators:
        if isinstance(item, dict) and item.get("name"):
            by_name.setdefault(item["name"], []).append(item)
    return {
        name: matches[0]
        for name, matches in by_name.items()
        if len(matches) == 1
    }


async def _get_goal_contract_indicator_index(db: AsyncSession, goal_id: str) -> dict[str, dict]:
    goal = await db.get(Goal, goal_id)
    if not goal or not goal.performance_contract_id:
        return {}
    contract = await db.get(PerformanceContract, goal.performance_contract_id)
    if not contract:
        return {}
    return _contract_indicator_index(contract.contract_data)


def _not_found(resource: str) -> AppException:
    return AppException(404, "DO_001", f"{resource} not found")


def _invalid_checkin(message: str) -> AppException:
    return AppException(422, "DO_005", message)


async def _get_subordinate_ids(db: AsyncSession, manager_id: str) -> list[str]:
    direct_reports = (
        select(User.id.label("id"))
        .where(
            User.manager_id == manager_id,
            User.status == UserStatus.active,
            User.deleted_at.is_(None),
        )
        .cte("do_subordinate_ids", recursive=True)
    )
    descendants = (
        select(User.id.label("id"))
        .join(direct_reports, User.manager_id == direct_reports.c.id)
        .where(
            User.status == UserStatus.active,
            User.deleted_at.is_(None),
        )
    )
    subordinate_ids = direct_reports.union(descendants)
    result = await db.execute(select(subordinate_ids.c.id))
    return list(result.scalars().all())


async def _ensure_goal_access(
    db: AsyncSession,
    current_user: User,
    owner_user_id: str,
) -> None:
    if current_user.role in _ADMIN_ROLES or current_user.id == owner_user_id:
        return
    if current_user.role == UserRole.manager:
        subordinate_ids = await _get_subordinate_ids(db, current_user.id)
        if owner_user_id in subordinate_ids:
            return
    raise PermissionDeniedError("Cannot access check-ins for this goal")


async def _get_indicator_context(
    db: AsyncSession,
    indicator_id: str,
) -> tuple[Indicator, Goal, Period]:
    result = await db.execute(
        select(Indicator, Goal, Period)
        .join(Goal, Goal.id == Indicator.goal_id)
        .join(Period, Period.id == Goal.period_id)
        .join(User, User.id == Goal.owner_user_id)
        .where(
            Indicator.id == indicator_id,
            Indicator.deleted_at.is_(None),
            Goal.deleted_at.is_(None),
            Period.deleted_at.is_(None),
            User.deleted_at.is_(None),
            User.status == UserStatus.active,
        )
    )
    row = result.one_or_none()
    if row is None:
        raise _not_found("Indicator")
    return row[0], row[1], row[2]


async def _get_goal_context(
    db: AsyncSession,
    goal_id: str,
) -> tuple[Goal, Period]:
    result = await db.execute(
        select(Goal, Period)
        .join(Period, Period.id == Goal.period_id)
        .join(User, User.id == Goal.owner_user_id)
        .where(
            Goal.id == goal_id,
            Goal.deleted_at.is_(None),
            Period.deleted_at.is_(None),
            User.deleted_at.is_(None),
            User.status == UserStatus.active,
        )
    )
    row = result.one_or_none()
    if row is None:
        raise _not_found("Goal")
    return row[0], row[1]


def _raw_indicator_type(
    indicator: Indicator,
    contract_indicator: dict | None,
) -> str | None:
    raw_type = getattr(indicator, "indicator_type", None)
    if raw_type is None:
        raw_type = (contract_indicator or {}).get("type")
    if raw_type is None:
        return None
    return str(_enum_value(raw_type)).lower()


def _expected_checkin_type(
    indicator: Indicator,
    contract_indicator: dict | None,
) -> str:
    if indicator.redline:
        return "redline"
    score_method = _enum_value(indicator.score_method)
    if score_method == "binary":
        raise _invalid_checkin("Indicator score method conflicts with its redline flag")
    if score_method == "manual":
        return "qualitative"
    return "quantitative"


def _canonical_checkin_value(actual_value) -> dict:
    if isinstance(actual_value, BaseModel):
        actual_value = actual_value.model_dump()
    elif isinstance(actual_value, (int, float)) and not isinstance(actual_value, bool):
        # Keep direct service callers compatible while the HTTP schema stays strict.
        actual_value = {"value_type": "quantitative", "value": actual_value}
    try:
        return _CHECKIN_VALUE_ADAPTER.validate_python(actual_value).model_dump()
    except ValidationError as exc:
        raise _invalid_checkin("Invalid check-in value") from exc


def _checkin_scalar(actual_value: dict) -> int | float | str:
    if not isinstance(actual_value, dict) or "value" not in actual_value:
        raise _invalid_checkin("Stored check-in value is invalid")
    return actual_value["value"]


def _fallback_indicator_type(indicator) -> str:
    if indicator.redline:
        return "redline"
    if _enum_value(indicator.score_method) == "manual":
        return "qualitative"
    return _enum_value(indicator.direction)


def _target_display(indicator, contract_indicator: dict | None) -> str | None:
    if contract_indicator and contract_indicator.get("target_display"):
        return contract_indicator["target_display"]
    target = _format_number(indicator.target_value)
    if target is None:
        return None
    unit = contract_indicator.get("unit") if contract_indicator else None
    return f"{target}{unit}" if unit else target


def build_indicator_response(indicator, contract_indicator: dict | None = None) -> dict:
    indicator_type = _fallback_indicator_type(indicator)
    return {
        "id": indicator.id,
        "goal_id": indicator.goal_id,
        "name": indicator.name,
        "definition": indicator.definition,
        "direction": _enum_value(indicator.direction),
        "weight": indicator.weight,
        "target_value": indicator.target_value,
        "score_method": _enum_value(indicator.score_method),
        "redline": indicator.redline,
        "indicator_type": indicator_type,
        "unit": (contract_indicator or {}).get("unit"),
        "target_display": _target_display(indicator, contract_indicator),
        "target_logic": (contract_indicator or {}).get("target_logic"),
        "scoring_rule": (contract_indicator or {}).get("scoring_rule"),
        "created_at": indicator.created_at,
    }


# Goals and Indicators
async def get_goal_by_user(
    db: AsyncSession,
    current_user: User,
    user_id: str,
    period_id: str,
):
    await _ensure_goal_access(db, current_user, user_id)
    query = (
        select(Goal)
        .join(Period, Period.id == Goal.period_id)
        .where(
            Goal.owner_user_id == user_id,
            Goal.period_id == period_id,
            Goal.deleted_at.is_(None),
            Period.user_id == user_id,
            Period.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    return result.scalars().first()


async def get_current_goal(db: AsyncSession, current_user: User, period_id: str):
    return await get_goal_by_user(db, current_user, current_user.id, period_id)


async def list_goal_indicators(
    db: AsyncSession,
    current_user: User,
    goal_id: str,
):
    goal, _period = await _get_goal_context(db, goal_id)
    await _ensure_goal_access(db, current_user, goal.owner_user_id)
    query = select(Indicator).where(
        Indicator.goal_id == goal_id,
        Indicator.deleted_at.is_(None),
    )
    result = await db.execute(query)
    indicators = result.scalars().all()
    contract_indicators = await _get_goal_contract_indicator_index(db, goal_id)
    return [
        build_indicator_response(indicator, contract_indicators.get(indicator.name))
        for indicator in indicators
    ]


# Data Checkins
async def submit_checkin(
    db: AsyncSession,
    current_user: User,
    indicator_id: str,
    actual_value,
    progress_description: str | None = None,
    issues: str | None = None,
):
    from core.exceptions import PeriodNotOpenError

    indicator, goal, period = await _get_indicator_context(db, indicator_id)
    await _ensure_goal_access(db, current_user, goal.owner_user_id)

    if period.status != PeriodStatus.open:
        raise PeriodNotOpenError()

    contract_indicators = await _get_goal_contract_indicator_index(db, goal.id)
    expected_type = _expected_checkin_type(
        indicator, contract_indicators.get(indicator.name)
    )
    canonical_value = _canonical_checkin_value(actual_value)
    if canonical_value["value_type"] != expected_type:
        raise _invalid_checkin(
            f"Expected {expected_type} value for this indicator"
        )

    checkin = DataCheckin(
        indicator_id=indicator_id,
        user_id=current_user.id,
        actual_value=canonical_value,
        progress_description=progress_description,
        issues=issues,
        submitted_at=datetime.now(timezone.utc)
    )
    db.add(checkin)
    await db.commit()
    await db.refresh(checkin)
    return checkin


async def _get_checkin_context(
    db: AsyncSession,
    checkin_id: str,
) -> tuple[DataCheckin, Indicator, Goal, Period]:
    checkin = await db.get(DataCheckin, checkin_id)
    if checkin is None:
        raise _not_found("Data check-in")
    indicator, goal, period = await _get_indicator_context(db, checkin.indicator_id)
    return checkin, indicator, goal, period


async def get_checkin(
    db: AsyncSession,
    current_user: User,
    checkin_id: str,
):
    checkin, _indicator, goal, _period = await _get_checkin_context(db, checkin_id)
    await _ensure_goal_access(db, current_user, goal.owner_user_id)
    return checkin


async def update_checkin(
    db: AsyncSession,
    current_user: User,
    checkin_id: str,
    actual_value=None,
    progress_description: str | None = None,
    issues: str | None = None,
):
    checkin, indicator, goal, period = await _get_checkin_context(db, checkin_id)
    await _ensure_goal_access(db, current_user, goal.owner_user_id)
    if period.status != PeriodStatus.open:
        from core.exceptions import PeriodNotOpenError

        raise PeriodNotOpenError()
    if actual_value is not None:
        contract_indicators = await _get_goal_contract_indicator_index(db, goal.id)
        expected_type = _expected_checkin_type(
            indicator, contract_indicators.get(indicator.name)
        )
        canonical_value = _canonical_checkin_value(actual_value)
        if canonical_value["value_type"] != expected_type:
            raise _invalid_checkin(
                f"Expected {expected_type} value for this indicator"
            )
        checkin.actual_value = canonical_value
    if progress_description is not None:
        checkin.progress_description = progress_description
    if issues is not None:
        checkin.issues = issues
    await db.commit()
    await db.refresh(checkin)
    return checkin


async def list_indicator_checkins(
    db: AsyncSession,
    current_user: User,
    indicator_id: str,
):
    _indicator, goal, _period = await _get_indicator_context(db, indicator_id)
    await _ensure_goal_access(db, current_user, goal.owner_user_id)
    query = select(DataCheckin).where(DataCheckin.indicator_id == indicator_id).order_by(DataCheckin.submitted_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


# Diagnostic Reports
async def generate_diagnostic_report(db: AsyncSession, current_user: User, goal_id: str, feedback: str | None = None):
    from core.exceptions import DiagnosticReportGenerationError
    from graphs.d_graph import run_d_stage

    try:
        goal, _period = await _get_goal_context(db, goal_id)
    except AppException as exc:
        raise DiagnosticReportGenerationError("Goal not found") from exc
    await _ensure_goal_access(db, current_user, goal.owner_user_id)

    query = select(Indicator).where(
        Indicator.goal_id == goal_id,
        Indicator.deleted_at.is_(None),
    )
    result = await db.execute(query)
    indicators = list(result.scalars().all())
    contract_indicators = await _get_goal_contract_indicator_index(db, goal_id)

    indicator_ids = [indicator.id for indicator in indicators]
    checkin_result = await db.execute(
        select(DataCheckin)
        .where(DataCheckin.indicator_id.in_(indicator_ids))
        .order_by(
            DataCheckin.indicator_id,
            DataCheckin.submitted_at.desc(),
            DataCheckin.id.desc(),
        )
    )
    latest_checkins: dict[str, DataCheckin] = {}
    for checkin in checkin_result.scalars().all():
        latest_checkins.setdefault(checkin.indicator_id, checkin)

    indicators_data = []
    actuals = {}
    for ind in indicators:
        latest_checkin = latest_checkins.get(ind.id)
        actual_val = _checkin_scalar(latest_checkin.actual_value) if latest_checkin else 0
        actuals[ind.id] = actual_val

        contract_indicator = contract_indicators.get(ind.name, {})
        raw_type = _raw_indicator_type(ind, contract_indicator)
        indicator_type = raw_type or (
            "redline" if ind.redline else _enum_value(ind.direction)
        )
        if indicator_type == "quantitative":
            indicator_type = _enum_value(ind.direction)

        indicators_data.append({
            "indicator_id": ind.id,
            "name": ind.name,
            "type": indicator_type,
            "target": ind.target_value if ind.target_value is not None else 0,
            "target_display": _target_display(ind, contract_indicator) or str(ind.target_value or 0),
            "weight": ind.weight * 100,
            "is_redline": ind.redline
        })

    try:
        d_result = run_d_stage(indicators_data, actuals, feedback)
        feedback_text = normalize_markdown_text(d_result.get("feedback_text", ""))

        report = DiagnosticReport(
            goal_id=goal_id,
            user_id=goal.owner_user_id,
            report_date=date.today(),
            overall_progress=d_result["d_result"].get("overall_progress"),
            weighted_achievement_rate=d_result["d_result"]["weighted_achievement"],
            time_progress=d_result["d_result"].get("time_progress"),
            progress_deviation=d_result["d_result"]["deviation"],
            indicators_analysis={"indicator_results": d_result["d_result"]["indicator_results"]},
            root_cause_analysis={"content": feedback_text},
            improvement_suggestions={"feedback": feedback_text},
            traffic_light_status=d_result["d_result"]["overall_status"],
            generated_by_ai=True
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report
    except Exception as e:
        raise DiagnosticReportGenerationError(str(e))


async def get_diagnostic_report(
    db: AsyncSession,
    current_user: User,
    report_id: str,
):
    report = await db.get(DiagnosticReport, report_id)
    if report is None:
        raise _not_found("Diagnostic report")
    goal, _period = await _get_goal_context(db, report.goal_id)
    await _ensure_goal_access(db, current_user, goal.owner_user_id)
    return report


async def list_goal_reports(db: AsyncSession, current_user: User, goal_id: str):
    goal, _period = await _get_goal_context(db, goal_id)
    await _ensure_goal_access(db, current_user, goal.owner_user_id)
    query = select(DiagnosticReport).where(DiagnosticReport.goal_id == goal_id).order_by(DiagnosticReport.report_date.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def get_latest_report(db: AsyncSession, current_user: User, goal_id: str):
    goal, _period = await _get_goal_context(db, goal_id)
    await _ensure_goal_access(db, current_user, goal.owner_user_id)
    query = select(DiagnosticReport).where(DiagnosticReport.goal_id == goal_id).order_by(DiagnosticReport.created_at.desc()).limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()


# Coaching Requests
async def create_coaching_request(db: AsyncSession, current_user: User, diagnostic_report_id: str, request_reason: str | None = None, urgency_level: str = "normal"):
    from core.exceptions import CoachingRequestNotFoundError

    try:
        await get_diagnostic_report(db, current_user, diagnostic_report_id)
    except AppException as exc:
        if exc.status_code == 404:
            raise CoachingRequestNotFoundError() from exc
        raise

    user = await db.get(User, current_user.id)
    manager_id = user.manager_id if user.manager_id else current_user.id

    request = CoachingRequest(
        diagnostic_report_id=diagnostic_report_id,
        requester_id=current_user.id,
        manager_id=manager_id,
        request_reason=request_reason,
        urgency_level=urgency_level
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request


async def get_coaching_request(
    db: AsyncSession,
    current_user: User,
    request_id: str,
):
    from core.exceptions import CoachingRequestNotFoundError
    request = await db.get(CoachingRequest, request_id)
    if not request:
        raise CoachingRequestNotFoundError()
    if (
        current_user.role not in _ADMIN_ROLES
        and current_user.id not in (request.requester_id, request.manager_id)
    ):
        raise PermissionDeniedError("Cannot access this coaching request")
    return request


async def update_request_status(
    db: AsyncSession,
    current_user: User,
    request_id: str,
    status: str,
    response: str | None = None,
):
    request = await get_coaching_request(db, current_user, request_id)
    if current_user.role not in _ADMIN_ROLES and current_user.id != request.manager_id:
        raise PermissionDeniedError("Only the assigned manager can update this request")
    request.status = status
    if response:
        request.notes = response
    await db.commit()
    await db.refresh(request)
    return request


async def _enrich_with_goal_id(db: AsyncSession, requests: list) -> list:
    if not requests:
        return requests
    report_ids = list({r.diagnostic_report_id for r in requests})
    result = await db.execute(
        select(DiagnosticReport.id, DiagnosticReport.goal_id)
        .where(DiagnosticReport.id.in_(report_ids))
    )
    goal_map = {row[0]: row[1] for row in result.all()}
    for req in requests:
        req.goal_id = goal_map.get(req.diagnostic_report_id)
    return requests


async def list_my_requests(db: AsyncSession, current_user: User):
    query = select(CoachingRequest).where(CoachingRequest.requester_id == current_user.id).order_by(CoachingRequest.created_at.desc())
    result = await db.execute(query)
    return await _enrich_with_goal_id(db, list(result.scalars().all()))


async def list_team_requests(db: AsyncSession, current_user: User):
    query = select(CoachingRequest).where(CoachingRequest.manager_id == current_user.id).order_by(CoachingRequest.created_at.desc())
    result = await db.execute(query)
    return await _enrich_with_goal_id(db, list(result.scalars().all()))


