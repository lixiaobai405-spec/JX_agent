import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.v1.check.service import generate_evaluation_tasks, submit_evaluation
from core.database import Base
from core.exceptions import AppException
from models.check_phase import (
    Evaluation,
    EvaluationTask,
    EvaluationTaskStatus,
    Goal,
    Indicator,
    IndicatorDirection,
    ScoreMethod,
    SelfAssessment,
    SelfAssessmentStatus,
)
from models.period import Period, PeriodStatus
from models.user import User, UserRole

# Import tables referenced by foreign keys in the test schema.
import models.action_phase  # noqa: F401
import models.organization  # noqa: F401
import models.plan_phase  # noqa: F401


class EvaluationSubmissionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name, "evaluation.db").as_posix()
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{database_path}",
            connect_args={"timeout": 30},
        )
        self.Session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with self.engine.begin() as conn:
            await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
            await conn.run_sync(Base.metadata.create_all)

        self.owner = self._user("owner")
        self.evaluator = self._user("evaluator", UserRole.manager)
        self.other_evaluator = self._user("other-evaluator", UserRole.manager)
        self.owner.manager_id = self.evaluator.id
        self.period = Period(
            id="period-1",
            user_id=self.owner.id,
            name="Period",
            start_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 7, 31, tzinfo=timezone.utc),
            status=PeriodStatus.open,
            d_phase_completed=True,
        )
        self.goal = Goal(
            id="goal-1",
            owner_user_id=self.owner.id,
            period_id=self.period.id,
            title="Goal",
            created_by=self.owner.id,
        )
        self.indicator = self._indicator("indicator-1", self.goal.id)
        self.other_indicator = self._indicator("indicator-2", self.goal.id)
        self.redline = self._indicator(
            "indicator-redline", self.goal.id, redline=True
        )
        self.task = self._task("task-1", self.goal.id, self.indicator.id)
        self.redline_task = self._task(
            "task-redline", self.goal.id, self.redline.id
        )
        self.assessment = SelfAssessment(
            id="assessment-1",
            goal_id=self.goal.id,
            user_id=self.owner.id,
            items={self.indicator.id: {"score": 80}},
            status=SelfAssessmentStatus.submitted,
            submitted_at=datetime.now(timezone.utc),
        )

        async with self.Session() as session:
            session.add_all(
                [
                    self.owner,
                    self.evaluator,
                    self.other_evaluator,
                    self.period,
                    self.goal,
                    self.indicator,
                    self.other_indicator,
                    self.redline,
                    self.task,
                    self.redline_task,
                    self.assessment,
                ]
            )
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()
        self.temp_dir.cleanup()

    @staticmethod
    def _user(user_id: str, role: UserRole = UserRole.employee) -> User:
        return User(
            id=user_id,
            username=user_id,
            full_name=user_id,
            email=f"{user_id}@example.com",
            hashed_password="hashed",
            role=role,
        )

    @staticmethod
    def _indicator(
        indicator_id: str,
        goal_id: str,
        redline: bool = False,
    ) -> Indicator:
        return Indicator(
            id=indicator_id,
            goal_id=goal_id,
            name=indicator_id,
            direction=(
                IndicatorDirection.negative if redline else IndicatorDirection.positive
            ),
            weight=0 if redline else 0.5,
            target_value=0 if redline else 100,
            score_method=ScoreMethod.binary if redline else ScoreMethod.ratio,
            redline=redline,
        )

    def _task(self, task_id: str, goal_id: str, indicator_id: str) -> EvaluationTask:
        now = datetime.now(timezone.utc)
        return EvaluationTask(
            id=task_id,
            goal_id=goal_id,
            indicator_id=indicator_id,
            evaluator_user_id=self.evaluator.id,
            assigned_by=self.evaluator.id,
            status=EvaluationTaskStatus.pending,
            assigned_at=now,
            due_at=now,
        )

    async def _assert_no_evaluation(self, task_id: str = "task-1") -> None:
        async with self.Session() as session:
            count = await session.scalar(
                select(func.count(Evaluation.id)).where(Evaluation.task_id == task_id)
            )
            task = await session.get(EvaluationTask, task_id)
        self.assertEqual(count, 0)
        self.assertEqual(task.status, EvaluationTaskStatus.pending)

    async def test_only_assigned_evaluator_can_submit(self):
        async with self.Session() as session:
            with self.assertRaises(AppException) as denied:
                await submit_evaluation(
                    session,
                    self.other_evaluator,
                    self.task.id,
                    self.indicator.id,
                    88,
                )

        self.assertEqual(denied.exception.status_code, 403)
        await self._assert_no_evaluation()

    async def test_task_indicator_must_match_request_and_goal(self):
        async with self.Session() as session:
            with self.assertRaises(AppException) as mismatch:
                await submit_evaluation(
                    session,
                    self.evaluator,
                    self.task.id,
                    self.other_indicator.id,
                    88,
                )

        self.assertEqual(mismatch.exception.status_code, 422)
        await self._assert_no_evaluation()

    async def test_soft_deleted_task_indicator_or_goal_is_rejected(self):
        for object_type in ("task", "indicator", "goal"):
            async with self.Session() as session:
                target = {
                    "task": await session.get(EvaluationTask, self.task.id),
                    "indicator": await session.get(Indicator, self.indicator.id),
                    "goal": await session.get(Goal, self.goal.id),
                }[object_type]
                target.deleted_at = datetime.now(timezone.utc)
                await session.commit()

                with self.assertRaises(AppException) as missing:
                    await submit_evaluation(
                        session,
                        self.evaluator,
                        self.task.id,
                        self.indicator.id,
                        88,
                    )
                self.assertEqual(missing.exception.status_code, 404)

                target.deleted_at = None
                await session.commit()

        await self._assert_no_evaluation()

    async def test_redline_indicator_cannot_be_evaluated(self):
        async with self.Session() as session:
            with self.assertRaises(AppException) as invalid:
                await submit_evaluation(
                    session,
                    self.evaluator,
                    self.redline_task.id,
                    self.redline.id,
                    88,
                )

        self.assertEqual(invalid.exception.status_code, 422)
        await self._assert_no_evaluation(self.redline_task.id)

    async def test_session_bound_current_evaluator_can_submit(self):
        async with self.Session() as session:
            evaluator = await session.get(User, self.evaluator.id)
            evaluation = await submit_evaluation(
                session,
                evaluator,
                self.task.id,
                self.indicator.id,
                88,
            )

        self.assertEqual(evaluation.evaluator_id, self.evaluator.id)

    async def test_two_sessions_cannot_double_submit_the_same_task(self):
        async with self.Session() as first, self.Session() as second:
            results = await asyncio.gather(
                submit_evaluation(
                    first,
                    self.evaluator,
                    self.task.id,
                    self.indicator.id,
                    88,
                    "first",
                ),
                submit_evaluation(
                    second,
                    self.evaluator,
                    self.task.id,
                    self.indicator.id,
                    92,
                    "second",
                ),
                return_exceptions=True,
            )

        evaluations = [result for result in results if isinstance(result, Evaluation)]
        conflicts = [
            result
            for result in results
            if isinstance(result, AppException) and result.status_code == 409
        ]
        self.assertEqual(len(evaluations), 1)
        self.assertEqual(len(conflicts), 1)

        async with self.Session() as session:
            stored = list(
                (
                    await session.execute(
                        select(Evaluation).where(Evaluation.task_id == self.task.id)
                    )
                )
                .scalars()
                .all()
            )
            task = await session.get(EvaluationTask, self.task.id)

        self.assertEqual(len(stored), 1)
        self.assertEqual(task.status, EvaluationTaskStatus.completed)
        self.assertIn(stored[0].score, (88, 92))

    async def test_two_sessions_generate_one_task_per_indicator(self):
        async with self.Session() as session:
            existing = await session.get(EvaluationTask, self.task.id)
            existing.deleted_at = datetime.now(timezone.utc)
            await session.commit()

        async def generate():
            async with self.Session() as session:
                manager = await session.get(User, self.evaluator.id)
                return await generate_evaluation_tasks(
                    session,
                    manager,
                    self.goal.id,
                )

        results = await asyncio.gather(generate(), generate())
        self.assertEqual([len(result) for result in results], [2, 2])

        async with self.Session() as session:
            tasks = list(
                (
                    await session.execute(
                        select(EvaluationTask).where(
                            EvaluationTask.goal_id == self.goal.id,
                            EvaluationTask.evaluator_user_id == self.evaluator.id,
                            EvaluationTask.indicator_id.in_(
                                (self.indicator.id, self.other_indicator.id)
                            ),
                            EvaluationTask.deleted_at.is_(None),
                        )
                    )
                )
                .scalars()
                .all()
            )

        self.assertEqual(len(tasks), 2)
        self.assertEqual({task.indicator_id for task in tasks}, {
            self.indicator.id,
            self.other_indicator.id,
        })


if __name__ == "__main__":
    unittest.main()
