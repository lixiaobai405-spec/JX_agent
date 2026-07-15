import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.v1.check import service as check_service
from api.v1.check.service import generate_final_result
from core.database import Base
from core.exceptions import AppException, WeightValidationError
from models.check_phase import (
    Evaluation,
    EvaluationTask,
    EvaluationTaskStatus,
    FinalResult,
    Goal,
    Indicator,
    IndicatorDirection,
    ScoreAggregate,
    ScoreMethod,
)
from models.do_phase import DataCheckin
from models.period import Period, PeriodStatus
from models.user import User, UserRole

# Import tables referenced by foreign keys in the test schema.
import models.action_phase  # noqa: F401
import models.organization  # noqa: F401
import models.plan_phase  # noqa: F401


class FinalResultIntegrityTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.Session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.owner = self._user("owner")
        self.evaluator = self._user("evaluator", UserRole.manager)
        self.period = self._period("period-1", self.owner.id, PeriodStatus.open)
        self.goal = Goal(
            id="goal-1",
            owner_user_id=self.owner.id,
            period_id=self.period.id,
            title="Goal",
            created_by=self.owner.id,
        )
        self.first_indicator = self._indicator(
            "indicator-1", self.goal.id, "Same display name", 0.4
        )
        self.second_indicator = self._indicator(
            "indicator-2", self.goal.id, "Same display name", 0.6
        )
        self.first_redline = self._indicator(
            "redline-1", self.goal.id, "Redline", 0, redline=True
        )
        self.second_redline = self._indicator(
            "redline-2", self.goal.id, "Redline", 0, redline=True
        )

        async with self.Session() as session:
            session.add_all(
                [
                    self.owner,
                    self.evaluator,
                    self.period,
                    self.goal,
                    self.first_indicator,
                    self.second_indicator,
                    self.first_redline,
                    self.second_redline,
                ]
            )
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

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
    def _period(
        period_id: str,
        user_id: str,
        status: PeriodStatus,
    ) -> Period:
        return Period(
            id=period_id,
            user_id=user_id,
            name=period_id,
            start_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 7, 31, tzinfo=timezone.utc),
            status=status,
        )

    @staticmethod
    def _indicator(
        indicator_id: str,
        goal_id: str,
        name: str,
        weight: float,
        redline: bool = False,
    ) -> Indicator:
        return Indicator(
            id=indicator_id,
            goal_id=goal_id,
            name=name,
            direction=(
                IndicatorDirection.negative if redline else IndicatorDirection.positive
            ),
            weight=weight,
            target_value=0 if redline else 100,
            score_method=ScoreMethod.binary if redline else ScoreMethod.ratio,
            redline=redline,
        )

    def _task_and_evaluation(
        self,
        suffix: str,
        indicator: Indicator,
        score: float,
        *,
        evaluation_deleted: bool = False,
    ) -> tuple[EvaluationTask, Evaluation]:
        now = datetime.now(timezone.utc)
        task = EvaluationTask(
            id=f"task-{suffix}",
            goal_id=self.goal.id,
            indicator_id=indicator.id,
            evaluator_user_id=self.evaluator.id,
            assigned_by=self.evaluator.id,
            status=EvaluationTaskStatus.completed,
            assigned_at=now,
            due_at=now,
        )
        evaluation = Evaluation(
            id=f"evaluation-{suffix}",
            task_id=task.id,
            goal_id=self.goal.id,
            indicator_id=indicator.id,
            evaluator_id=self.evaluator.id,
            score=score,
            deleted_at=now if evaluation_deleted else None,
        )
        return task, evaluation

    async def test_missing_or_soft_deleted_evaluation_blocks_final_result(self):
        first_task, first_evaluation = self._task_and_evaluation(
            "first", self.first_indicator, 80
        )
        second_task, second_evaluation = self._task_and_evaluation(
            "second", self.second_indicator, 100, evaluation_deleted=True
        )
        async with self.Session() as session:
            session.add_all(
                [first_task, first_evaluation, second_task, second_evaluation]
            )
            await session.commit()

            with patch("graphs.c_graph.run_c_stage") as run_c_stage:
                with self.assertRaises(AppException) as incomplete:
                    await generate_final_result(
                        session, self.evaluator, self.goal.id
                    )

            self.assertIn(incomplete.exception.status_code, (409, 422))
            run_c_stage.assert_not_called()

        async with self.Session() as session:
            aggregate_count = await session.scalar(
                select(func.count(ScoreAggregate.id))
            )
            final_count = await session.scalar(select(func.count(FinalResult.id)))
        self.assertEqual(aggregate_count, 0)
        self.assertEqual(final_count, 0)

    async def test_scores_by_indicator_id_and_uses_latest_redline_checkins(self):
        first_task, first_evaluation = self._task_and_evaluation(
            "first", self.first_indicator, 80
        )
        second_task, second_evaluation = self._task_and_evaluation(
            "second", self.second_indicator, 100
        )
        now = datetime.now(timezone.utc)
        checkins = [
            DataCheckin(
                id="redline-1-old",
                indicator_id=self.first_redline.id,
                user_id=self.owner.id,
                actual_value={"value_type": "redline", "value": 5},
                submitted_at=now - timedelta(days=1),
            ),
            DataCheckin(
                id="redline-1-latest",
                indicator_id=self.first_redline.id,
                user_id=self.owner.id,
                actual_value={"value_type": "redline", "value": 1},
                submitted_at=now,
            ),
            DataCheckin(
                id="redline-2-legacy",
                indicator_id=self.second_redline.id,
                user_id=self.owner.id,
                actual_value={"value": 2},
                submitted_at=now,
            ),
        ]

        async with self.Session() as session:
            session.add_all(
                [
                    first_task,
                    first_evaluation,
                    second_task,
                    second_evaluation,
                    *checkins,
                ]
            )
            await session.commit()

            def fake_run_c_stage(
                indicator_results,
                supervisor_scores,
                _supervisor_comment,
                redline_triggered,
                redline_count,
                _position_name,
                _assessment_period,
            ):
                self.assertEqual(
                    supervisor_scores,
                    {
                        self.first_indicator.id: 80,
                        self.second_indicator.id: 100,
                    },
                )
                self.assertEqual(
                    {item["indicator_id"] for item in indicator_results},
                    {
                        self.first_indicator.id,
                        self.second_indicator.id,
                        self.first_redline.id,
                        self.second_redline.id,
                    },
                )
                self.assertTrue(redline_triggered)
                self.assertEqual(redline_count, 3)
                return {"c_result": {}, "result_sheet_text": "result"}

            with patch(
                "graphs.c_graph.run_c_stage", side_effect=fake_run_c_stage
            ):
                final_result = await generate_final_result(
                    session, self.evaluator, self.goal.id
                )

            aggregate = await session.scalar(
                select(ScoreAggregate).where(ScoreAggregate.goal_id == self.goal.id)
            )

        self.assertEqual(final_result.final_grade, "C")
        self.assertEqual(aggregate.final_score, 32)
        self.assertEqual(aggregate.breakdown["raw_score"], 92)
        self.assertEqual(aggregate.breakdown["deductions"], 60)
        self.assertEqual(
            {item["indicator_id"] for item in aggregate.breakdown["indicator_scores"]},
            {self.first_indicator.id, self.second_indicator.id},
        )

    async def test_invalid_regular_indicator_weights_block_final_result(self):
        first_task, first_evaluation = self._task_and_evaluation(
            "first", self.first_indicator, 80
        )
        second_task, second_evaluation = self._task_and_evaluation(
            "second", self.second_indicator, 100
        )
        async with self.Session() as session:
            session.add_all(
                [first_task, first_evaluation, second_task, second_evaluation]
            )
            second_indicator = await session.get(Indicator, self.second_indicator.id)
            second_indicator.weight = 0.5
            await session.commit()

            with patch("graphs.c_graph.run_c_stage") as run_c_stage:
                with self.assertRaises(WeightValidationError):
                    await generate_final_result(
                        session, self.evaluator, self.goal.id
                    )
            run_c_stage.assert_not_called()


class PendingEvaluationCountTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.Session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.evaluator = FinalResultIntegrityTest._user(
            "evaluator", UserRole.manager
        )
        self.other_evaluator = FinalResultIntegrityTest._user(
            "other-evaluator", UserRole.manager
        )
        self.owners = [
            FinalResultIntegrityTest._user(f"owner-{index}")
            for index in range(1, 8)
        ]

        async with self.Session() as session:
            session.add_all([self.evaluator, self.other_evaluator, *self.owners])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _add_pending_case(
        self,
        session: AsyncSession,
        suffix: str,
        owner: User,
        *,
        period_status: PeriodStatus = PeriodStatus.open,
        evaluator: User | None = None,
        task_status: EvaluationTaskStatus = EvaluationTaskStatus.pending,
        deleted: str | None = None,
    ) -> None:
        period = FinalResultIntegrityTest._period(
            f"period-{suffix}", owner.id, period_status
        )
        goal = Goal(
            id=f"goal-{suffix}",
            owner_user_id=owner.id,
            period_id=period.id,
            title=suffix,
            created_by=owner.id,
        )
        indicator = FinalResultIntegrityTest._indicator(
            f"indicator-{suffix}", goal.id, suffix, 1
        )
        now = datetime.now(timezone.utc)
        task = EvaluationTask(
            id=f"task-{suffix}",
            goal_id=goal.id,
            indicator_id=indicator.id,
            evaluator_user_id=(evaluator or self.evaluator).id,
            assigned_by=self.evaluator.id,
            status=task_status,
            assigned_at=now,
            due_at=now,
        )
        if deleted == "period":
            period.deleted_at = now
        elif deleted == "goal":
            goal.deleted_at = now
        elif deleted == "indicator":
            indicator.deleted_at = now
        elif deleted == "task":
            task.deleted_at = now
        session.add_all([period, goal, indicator, task])

    async def test_count_is_distinct_goal_owners_for_only_valid_pending_tasks(self):
        async with self.Session() as session:
            await self._add_pending_case(session, "owner-1-a", self.owners[0])
            await self._add_pending_case(session, "owner-1-b", self.owners[0])
            await self._add_pending_case(
                session,
                "owner-2-draft",
                self.owners[1],
                period_status=PeriodStatus.draft,
            )
            await self._add_pending_case(
                session,
                "wrong-evaluator",
                self.owners[2],
                evaluator=self.other_evaluator,
            )
            await self._add_pending_case(
                session,
                "completed",
                self.owners[3],
                task_status=EvaluationTaskStatus.completed,
            )
            await self._add_pending_case(
                session,
                "closed",
                self.owners[4],
                period_status=PeriodStatus.closed,
            )
            await self._add_pending_case(
                session, "deleted-goal", self.owners[5], deleted="goal"
            )
            await self._add_pending_case(
                session,
                "deleted-indicator",
                self.owners[5],
                deleted="indicator",
            )
            await self._add_pending_case(
                session, "deleted-task", self.owners[5], deleted="task"
            )
            await self._add_pending_case(
                session, "deleted-period", self.owners[6], deleted="period"
            )
            await session.commit()

            count = await check_service.get_my_pending_evaluation_count(
                session, self.evaluator
            )

        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
