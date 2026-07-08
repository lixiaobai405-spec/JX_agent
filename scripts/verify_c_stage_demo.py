import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from api.v1.check import service as check_service
from core.database import AsyncSessionLocal
from models.check_phase import (
    Evaluation,
    EvaluationTask,
    EvaluationTaskStatus,
    FinalResult,
    FinalResultStatus,
    Goal,
    Indicator,
    ScoreAggregate,
    SelfAssessment,
    SelfAssessmentStatus,
)
from models.period import Period
from models.user import User
from scripts.verify_d_stage_demo import verify_d_stage_demo


SELF_ASSESSMENT_ITEMS = {
    "区域净销售额": {"actual": 520, "self_score": 75, "comment": "核心便利系统铺货推进中，但成交转化偏慢。"},
    "新品铺货率": {"actual": 70, "self_score": 78, "comment": "重点门店已进入谈判，部分门店排期延后。"},
    "销售回款率": {"actual": 96, "self_score": 92, "comment": "大客户回款整体稳定。"},
    "巡店SOP执行": {"actual": 90, "self_score": 90, "comment": "陈列和价签执行基本符合要求。"},
}

MANAGER_SCORES = {
    "区域净销售额": 76,
    "新品铺货率": 80,
    "销售回款率": 92,
    "巡店SOP执行": 88,
}


def _assert_mock_mode() -> None:
    assert os.getenv("USE_MOCK", "").lower() == "true", "Run with USE_MOCK=true"


async def _scalar_one(session, model, *conditions):
    result = await session.execute(select(model).where(*conditions))
    return result.scalar_one()


async def _latest_self_assessment(session, goal_id: str) -> SelfAssessment | None:
    result = await session.execute(
        select(SelfAssessment)
        .where(SelfAssessment.goal_id == goal_id, SelfAssessment.deleted_at.is_(None))
        .order_by(SelfAssessment.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _ensure_self_assessment(session, user: User, goal: Goal) -> SelfAssessment:
    assessment = await _latest_self_assessment(session, goal.id)
    if not assessment:
        assessment = await check_service.create_self_assessment(
            session,
            current_user=user,
            goal_id=goal.id,
            items=SELF_ASSESSMENT_ITEMS,
        )
    elif assessment.status == SelfAssessmentStatus.draft:
        assessment = await check_service.update_self_assessment(
            session,
            assessment_id=assessment.id,
            items=SELF_ASSESSMENT_ITEMS,
        )

    if assessment.status == SelfAssessmentStatus.draft:
        assessment = await check_service.submit_self_assessment(session, assessment.id)

    assert assessment.status == SelfAssessmentStatus.submitted, assessment.status
    return assessment


async def _tasks_for_goal(session, goal_id: str) -> list[EvaluationTask]:
    result = await session.execute(
        select(EvaluationTask).where(
            EvaluationTask.goal_id == goal_id,
            EvaluationTask.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


async def _ensure_evaluation_tasks(session, manager: User, goal: Goal, scorable_indicators: list[Indicator]) -> list[EvaluationTask]:
    await check_service.generate_evaluation_tasks(session, current_user=manager, goal_id=goal.id)
    await check_service.generate_evaluation_tasks(session, current_user=manager, goal_id=goal.id)

    tasks = await _tasks_for_goal(session, goal.id)
    assert len(tasks) == len(scorable_indicators), (
        f"Expected one task per indicator, got {len(tasks)} tasks for {len(scorable_indicators)} indicators"
    )
    return tasks


async def _submit_manager_evaluations(session, manager: User, tasks: list[EvaluationTask], indicators_by_id: dict[str, Indicator]) -> None:
    for task in tasks:
        if task.status == EvaluationTaskStatus.completed:
            continue
        indicator = indicators_by_id[task.indicator_id]
        await check_service.submit_evaluation(
            session,
            current_user=manager,
            task_id=task.id,
            indicator_id=indicator.id,
            score=MANAGER_SCORES[indicator.name],
            comment=f"{indicator.name}经理评分",
        )


async def verify_c_stage_demo() -> None:
    _assert_mock_mode()
    await verify_d_stage_demo()

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

        period.d_phase_completed = True
        await session.commit()

        indicators_result = await session.execute(
            select(Indicator).where(
                Indicator.goal_id == goal.id,
                Indicator.deleted_at.is_(None),
            )
        )
        indicators = list(indicators_result.scalars().all())
        scorable_indicators = [indicator for indicator in indicators if not indicator.redline]
        indicators_by_id = {indicator.id: indicator for indicator in scorable_indicators}

        await _ensure_self_assessment(session, user, goal)
        tasks = await _ensure_evaluation_tasks(session, manager, goal, scorable_indicators)
        await _submit_manager_evaluations(session, manager, tasks, indicators_by_id)

        completed_tasks = await _tasks_for_goal(session, goal.id)
        assert completed_tasks, "No evaluation tasks found"
        assert all(task.status == EvaluationTaskStatus.completed for task in completed_tasks), "Not all tasks completed"

        result = await check_service.generate_final_result(session, current_user=manager, goal_id=goal.id)
        if result.status != FinalResultStatus.confirmed:
            assert result.status == FinalResultStatus.pending, result.status
        assert result.final_grade in {"S", "A", "B", "C"}, result.final_grade

        score_aggregate = await _scalar_one(session, ScoreAggregate, ScoreAggregate.goal_id == goal.id)
        final_result = await _scalar_one(session, FinalResult, FinalResult.goal_id == goal.id)
        assert score_aggregate.final_score >= 0, score_aggregate.final_score
        assert final_result.id == result.id

        confirmed = (
            result
            if result.status == FinalResultStatus.confirmed
            else await check_service.confirm_final_result(session, result.id, current_user=manager)
        )
        assert confirmed.status == FinalResultStatus.confirmed, confirmed.status

    print("C_STAGE_DEMO_OK")


if __name__ == "__main__":
    asyncio.run(verify_c_stage_demo())
