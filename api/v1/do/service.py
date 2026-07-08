from datetime import datetime, timezone, date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.do_phase import DataCheckin, DiagnosticReport, CoachingRequest
from models.check_phase import Goal, Indicator
from models.user import User, UserRole
from models.period import Period


# Goals and Indicators
async def get_goal_by_user(db: AsyncSession, user_id: str, period_id: str):
    query = select(Goal).where(
        Goal.owner_user_id == user_id,
        Goal.period_id == period_id
    )
    result = await db.execute(query)
    return result.scalars().first()


async def get_current_goal(db: AsyncSession, current_user: User, period_id: str):
    return await get_goal_by_user(db, current_user.id, period_id)


async def list_goal_indicators(db: AsyncSession, goal_id: str):
    query = select(Indicator).where(Indicator.goal_id == goal_id)
    result = await db.execute(query)
    return result.scalars().all()


# Data Checkins
async def submit_checkin(db: AsyncSession, current_user: User, indicator_id: str, actual_value: float, progress_description: str | None = None, issues: str | None = None):
    from core.exceptions import PeriodNotOpenError

    indicator = await db.get(Indicator, indicator_id)
    goal = await db.get(Goal, indicator.goal_id)
    period = await db.get(Period, goal.period_id)

    if not period or period.status != "open":
        raise PeriodNotOpenError()

    checkin = DataCheckin(
        indicator_id=indicator_id,
        user_id=current_user.id,
        actual_value={"value": actual_value},
        progress_description=progress_description,
        issues=issues,
        submitted_at=datetime.now(timezone.utc)
    )
    db.add(checkin)
    await db.commit()
    await db.refresh(checkin)
    return checkin


async def get_checkin(db: AsyncSession, checkin_id: str):
    return await db.get(DataCheckin, checkin_id)


async def update_checkin(db: AsyncSession, checkin_id: str, actual_value: float | None = None, progress_description: str | None = None, issues: str | None = None):
    checkin = await get_checkin(db, checkin_id)
    if actual_value is not None:
        checkin.actual_value = {"value": actual_value}
    if progress_description is not None:
        checkin.progress_description = progress_description
    if issues is not None:
        checkin.issues = issues
    await db.commit()
    await db.refresh(checkin)
    return checkin


async def list_indicator_checkins(db: AsyncSession, indicator_id: str):
    query = select(DataCheckin).where(DataCheckin.indicator_id == indicator_id).order_by(DataCheckin.submitted_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


# Diagnostic Reports
async def generate_diagnostic_report(db: AsyncSession, current_user: User, goal_id: str, feedback: str | None = None):
    from core.exceptions import DiagnosticReportGenerationError
    from graphs.d_graph import run_d_stage

    goal = await db.get(Goal, goal_id)
    if not goal:
        raise DiagnosticReportGenerationError("Goal not found")

    query = select(Indicator).where(Indicator.goal_id == goal_id)
    result = await db.execute(query)
    indicators = result.scalars().all()

    indicators_data = []
    actuals = {}
    for ind in indicators:
        query = select(DataCheckin).where(DataCheckin.indicator_id == ind.id).order_by(DataCheckin.submitted_at.desc()).limit(1)
        result = await db.execute(query)
        latest_checkin = result.scalar_one_or_none()

        actual_val = latest_checkin.actual_value.get("value", 0) if latest_checkin else 0
        actuals[ind.name] = actual_val

        indicator_type = "redline" if ind.redline else ("positive" if ind.direction == "positive" else "negative")

        indicators_data.append({
            "name": ind.name,
            "type": indicator_type,
            "target": ind.target_value or 0,
            "target_display": str(ind.target_value or 0),
            "weight": ind.weight * 100,
            "is_redline": ind.redline
        })

    try:
        d_result = run_d_stage(indicators_data, actuals, feedback)

        report = DiagnosticReport(
            goal_id=goal_id,
            user_id=current_user.id,
            report_date=date.today(),
            overall_progress=d_result["d_result"].get("overall_progress"),
            weighted_achievement_rate=d_result["d_result"]["weighted_achievement"],
            time_progress=d_result["d_result"].get("time_progress"),
            progress_deviation=d_result["d_result"]["deviation"],
            indicators_analysis={"indicator_results": d_result["d_result"]["indicator_results"]},
            root_cause_analysis={"content": d_result.get("feedback_text", "")},
            improvement_suggestions={"feedback": d_result.get("feedback_text", "")},
            traffic_light_status=d_result["d_result"]["overall_status"],
            generated_by_ai=True
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report
    except Exception as e:
        raise DiagnosticReportGenerationError(str(e))


async def get_diagnostic_report(db: AsyncSession, report_id: str):
    return await db.get(DiagnosticReport, report_id)


async def list_goal_reports(db: AsyncSession, goal_id: str):
    query = select(DiagnosticReport).where(DiagnosticReport.goal_id == goal_id).order_by(DiagnosticReport.report_date.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def get_latest_report(db: AsyncSession, goal_id: str):
    query = select(DiagnosticReport).where(DiagnosticReport.goal_id == goal_id).order_by(DiagnosticReport.created_at.desc()).limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()


# Coaching Requests
async def create_coaching_request(db: AsyncSession, current_user: User, diagnostic_report_id: str, request_reason: str | None = None, urgency_level: str = "normal"):
    from core.exceptions import CoachingRequestNotFoundError

    report = await db.get(DiagnosticReport, diagnostic_report_id)
    if not report:
        raise CoachingRequestNotFoundError()

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


async def get_coaching_request(db: AsyncSession, request_id: str):
    from core.exceptions import CoachingRequestNotFoundError
    request = await db.get(CoachingRequest, request_id)
    if not request:
        raise CoachingRequestNotFoundError()
    return request


async def update_request_status(db: AsyncSession, request_id: str, status: str, response: str | None = None):
    request = await get_coaching_request(db, request_id)
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


