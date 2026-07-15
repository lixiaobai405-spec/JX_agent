import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from api.v1.action import service as action_service
from core.database import AsyncSessionLocal
from models.action_phase import DevelopmentPlan, DevelopmentPlanStatus, InheritanceSuggestion, SuggestionStatus, SuggestionType
from models.check_phase import FinalResult, Goal
from models.period import Period, PeriodStatus
from models.user import User
from scripts.verify_c_stage_demo import verify_c_stage_demo


DEVELOPMENT_PLAN_DATA = {
    "goals": {
        "text": "提升重点便利系统客户转化率，将华东区核心门店新品铺货率提升到85%以上。"
    },
    "actions": {
        "text": "每周复盘3个失败谈判案例，按客户类型调整报价话术；每周五向李娜提交铺货推进清单。"
    },
    "required_resources": {
        "text": "需要上级协助复盘重点客户谈判策略，并提供优秀KA案例。"
    },
    "timeline": {
        "text": "2026年8月底前完成第一轮重点门店复盘，2026年9月底前形成标准打法。"
    },
}


def _assert_mock_mode() -> None:
    assert os.getenv("USE_MOCK", "").lower() == "true", "Run with USE_MOCK=true"


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc).replace(tzinfo=None)


async def _scalar_one(session, model, *conditions):
    result = await session.execute(select(model).where(*conditions))
    return result.scalar_one()


async def _ensure_next_period(session, user: User) -> Period:
    result = await session.execute(
        select(Period).where(
            Period.user_id == user.id,
            Period.name == "2026年8月绩效演示周期",
            Period.deleted_at.is_(None),
        )
    )
    period = result.scalar_one_or_none()
    if not period:
        period = Period(
            user_id=user.id,
            name="2026年8月绩效演示周期",
            start_date=_dt("2026-08-01T00:00:00+00:00"),
            end_date=_dt("2026-08-31T23:59:59+00:00"),
            status=PeriodStatus.draft,
            d_phase_completed=False,
        )
        session.add(period)
    else:
        period.start_date = _dt("2026-08-01T00:00:00+00:00")
        period.end_date = _dt("2026-08-31T23:59:59+00:00")
    await session.commit()
    await session.refresh(period)
    return period


async def _latest_plan(session, report_id: str, user_id: str) -> DevelopmentPlan | None:
    result = await session.execute(
        select(DevelopmentPlan)
        .where(
            DevelopmentPlan.review_report_id == report_id,
            DevelopmentPlan.user_id == user_id,
            DevelopmentPlan.deleted_at.is_(None),
        )
        .order_by(DevelopmentPlan.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _ensure_plan(session, user: User, manager: User, report_id: str) -> DevelopmentPlan:
    plan = await _latest_plan(session, report_id, user.id)
    if not plan:
        plan = await action_service.create_development_plan(
            session,
            current_user=user,
            review_report_id=report_id,
            goals=DEVELOPMENT_PLAN_DATA["goals"],
            actions=DEVELOPMENT_PLAN_DATA["actions"],
            required_resources=DEVELOPMENT_PLAN_DATA["required_resources"],
            timeline=DEVELOPMENT_PLAN_DATA["timeline"],
        )
    elif plan.status == DevelopmentPlanStatus.draft:
        plan = await action_service.update_development_plan(
            session,
            user,
            plan.id,
            DEVELOPMENT_PLAN_DATA,
        )

    plan = await action_service.ai_review_plan(session, user, plan.id)
    assert plan.ai_reviewed is True
    assert plan.smart_evaluation, "Missing SMART evaluation"
    assert plan.ai_suggestions and plan.ai_suggestions.get("overall_review"), "Missing AI overall review"

    if plan.status == DevelopmentPlanStatus.draft:
        plan = await action_service.submit_plan(session, user, plan.id)
    if plan.status != DevelopmentPlanStatus.approved:
        plan = await action_service.approve_plan(session, manager, plan.id, approved=True)

    assert plan.status == DevelopmentPlanStatus.approved, plan.status
    assert plan.approved_by == manager.id
    assert plan.approved_at is not None
    return plan


async def _pending_suggestions(session, user_id: str, period_id: str) -> list[InheritanceSuggestion]:
    result = await session.execute(
        select(InheritanceSuggestion)
        .where(
            InheritanceSuggestion.user_id == user_id,
            InheritanceSuggestion.new_period_id == period_id,
            InheritanceSuggestion.status == SuggestionStatus.pending,
            InheritanceSuggestion.deleted_at.is_(None),
        )
        .order_by(InheritanceSuggestion.created_at.asc())
    )
    return list(result.scalars().all())


async def verify_a_stage_demo() -> None:
    _assert_mock_mode()
    await verify_c_stage_demo()

    async with AsyncSessionLocal() as session:
        user = await _scalar_one(session, User, User.username == "demo_sales")
        manager = await _scalar_one(session, User, User.username == "demo_manager")
        period = await _scalar_one(
            session,
            Period,
            Period.user_id == user.id,
            Period.name == "2026年7月绩效演示周期",
            Period.deleted_at.is_(None),
        )
        goal = await _scalar_one(
            session,
            Goal,
            Goal.owner_user_id == user.id,
            Goal.period_id == period.id,
            Goal.deleted_at.is_(None),
        )
        final_result = await _scalar_one(session, FinalResult, FinalResult.goal_id == goal.id)

        report = await action_service.generate_review_report(session, current_user=user, final_result_id=final_result.id)
        assert report.strengths_analysis and (
            report.strengths_analysis.get("strengths") or report.strengths_analysis.get("summary")
        ), "Missing strengths analysis"
        assert report.improvement_areas and report.improvement_areas.get("areas"), "Missing improvement areas"
        expected_report_type = "s_a" if final_result.final_grade in {"S", "A"} else final_result.final_grade.lower()
        assert report.report_type == expected_report_type, report.report_type

        plan = await _ensure_plan(session, user, manager, report.id)
        next_period = await _ensure_next_period(session, user)

        first = await action_service.generate_inheritance_suggestions(
            session,
            current_user=user,
            user_id=user.id,
            from_period_id=period.id,
            to_period_id=next_period.id,
        )
        second = await action_service.generate_inheritance_suggestions(
            session,
            current_user=user,
            user_id=user.id,
            from_period_id=period.id,
            to_period_id=next_period.id,
        )
        assert first and second

        pending = await _pending_suggestions(session, user.id, next_period.id)
        assert len(pending) >= 2, f"Need two pending suggestions, got {len(pending)}"
        assert all(item.suggestion_type == SuggestionType.new_indicator for item in pending[:2])

        accepted = await action_service.accept_suggestion(session, user, pending[0].id)
        rejected = await action_service.reject_suggestion(
            session,
            user,
            pending[1].id,
            "本期先聚焦销售转化，不纳入该建议",
        )
        assert accepted.status == SuggestionStatus.accepted
        assert rejected.status == SuggestionStatus.rejected

    print("A_STAGE_DEMO_OK")


if __name__ == "__main__":
    asyncio.run(verify_a_stage_demo())
