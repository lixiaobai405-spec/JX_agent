import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.v1.action.service import generate_review_report
from core.database import Base
from models.check_phase import (
    Evaluation,
    EvaluationTask,
    EvaluationTaskStatus,
    FinalResult,
    FinalResultStatus,
    Goal,
    Indicator,
    IndicatorDirection,
    ScoreAggregate,
    ScoreMethod,
)
from models.period import Period, PeriodStatus
from models.plan_phase import AIGenerationLog
from models.user import User, UserRole

# Import models with foreign keys referenced by the tables under test.
import models.action_phase  # noqa: F401
import models.organization  # noqa: F401
import models.plan_phase  # noqa: F401


class ReviewReportFallbackTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.Session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_generate_review_report_falls_back_when_ai_generation_fails(self):
        now = datetime.now(timezone.utc)

        async with self.Session() as session:
            employee = User(
                id="employee-1",
                username="demo_employee",
                full_name="测试员工",
                email="employee@example.com",
                hashed_password="hashed",
                role=UserRole.employee,
            )
            manager = User(
                id="manager-1",
                username="demo_manager",
                full_name="测试经理",
                email="manager@example.com",
                hashed_password="hashed",
                role=UserRole.manager,
            )
            period = Period(
                id="period-1",
                user_id=manager.id,
                name="测试考核期",
                start_date=now,
                end_date=now,
                status=PeriodStatus.open,
            )
            goal = Goal(
                id="goal-1",
                owner_user_id=employee.id,
                period_id=period.id,
                title="测试目标",
                created_by=manager.id,
            )
            strong_indicator = Indicator(
                id="indicator-strong",
                goal_id=goal.id,
                name="重复指标",
                direction=IndicatorDirection.positive,
                weight=0.6,
                target_value=100,
                score_method=ScoreMethod.ratio,
            )
            weak_indicator = Indicator(
                id="indicator-weak",
                goal_id=goal.id,
                name="重复指标",
                direction=IndicatorDirection.positive,
                weight=0.4,
                target_value=100,
                score_method=ScoreMethod.ratio,
            )
            redline_indicator = Indicator(
                id="indicator-redline",
                goal_id=goal.id,
                name="重复指标",
                direction=IndicatorDirection.negative,
                weight=0,
                target_value=0,
                score_method=ScoreMethod.binary,
                redline=True,
            )
            task = EvaluationTask(
                id="task-1",
                goal_id=goal.id,
                indicator_id=None,
                evaluator_user_id=manager.id,
                assigned_by=manager.id,
                status=EvaluationTaskStatus.completed,
                assigned_at=now,
                due_at=now,
            )
            strong_evaluation = Evaluation(
                id="evaluation-strong",
                task_id=task.id,
                goal_id=goal.id,
                indicator_id=strong_indicator.id,
                evaluator_id=manager.id,
                score=92,
            )
            weak_evaluation = Evaluation(
                id="evaluation-weak",
                task_id=task.id,
                goal_id=goal.id,
                indicator_id=weak_indicator.id,
                evaluator_id=manager.id,
                score=72,
            )
            redline_evaluation = Evaluation(
                id="evaluation-redline",
                task_id=task.id,
                goal_id=goal.id,
                indicator_id=redline_indicator.id,
                evaluator_id=manager.id,
                score=100,
            )
            score_aggregate = ScoreAggregate(
                id="score-aggregate-1",
                goal_id=goal.id,
                final_score=84,
                breakdown={
                    "indicator_scores": [
                        {"indicator_id": strong_indicator.id, "score": 92},
                        {"indicator_id": weak_indicator.id, "score": 72},
                        {"indicator_id": redline_indicator.id, "score": 100},
                    ]
                },
                computed_at=now,
            )
            final_result = FinalResult(
                id="final-result-1",
                goal_id=goal.id,
                computed_score_id=score_aggregate.id,
                suggested_grade="A",
                final_grade="A",
                confirmed_by=manager.id,
                confirmed_at=now,
                status=FinalResultStatus.confirmed,
            )

            session.add_all(
                [
                    employee,
                    manager,
                    period,
                    goal,
                    strong_indicator,
                    weak_indicator,
                    redline_indicator,
                    task,
                    strong_evaluation,
                    weak_evaluation,
                    redline_evaluation,
                    score_aggregate,
                    final_result,
                ]
            )
            await session.commit()
            employee_id = employee.id

            with patch(
                "api.v1.action.service.run_a_stage",
                side_effect=Exception("mock validation failed"),
            ):
                report = await generate_review_report(session, employee, final_result.id)

            self.assertFalse(report.ai_generated)
            self.assertEqual(report.report_type, "s_a")
            self.assertTrue(report.development_suggestions["fallback"])
            self.assertNotIn(
                "mock validation failed",
                report.development_suggestions["fallback_reason"],
            )
            self.assertEqual(len(report.strengths_analysis["strengths"]), 1)
            self.assertEqual(report.strengths_analysis["strengths"][0]["score"], 92)
            self.assertEqual(len(report.improvement_areas["areas"]), 1)
            self.assertEqual(report.improvement_areas["areas"][0]["score"], 72)

            log = await session.scalar(
                select(AIGenerationLog).where(
                    AIGenerationLog.job_type == "review_report",
                    AIGenerationLog.user_id == employee_id,
                )
            )
            self.assertIsNotNone(log)
            self.assertFalse(log.success)
            self.assertIn("mock validation failed", log.error_message)


if __name__ == "__main__":
    unittest.main()
