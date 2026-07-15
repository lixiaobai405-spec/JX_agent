import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.v1.check.service import (
    adjust_final_result,
    confirm_final_result,
    create_self_assessment,
    generate_evaluation_tasks,
    generate_final_result,
    get_final_result_by_goal,
    get_goal_self_assessment,
    get_my_pending_evaluation_tasks,
    get_self_assessment,
    list_evaluation_tasks,
    list_goal_evaluations,
    submit_self_assessment,
    update_self_assessment,
)
from core.database import Base
from core.exceptions import AppException
from models.check_phase import (
    Evaluation,
    EvaluationTask,
    EvaluationTaskStatus,
    FinalResult,
    FinalResultStatus,
    Goal,
    Indicator,
    IndicatorDirection,
    ScoreMethod,
    SelfAssessment,
    SelfAssessmentStatus,
)
from models.period import Period, PeriodStatus
from models.user import User, UserRole

import models.action_phase  # noqa: F401
import models.do_phase  # noqa: F401
import models.organization  # noqa: F401
import models.plan_phase  # noqa: F401


class CheckObjectPermissionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.Session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        self.manager = self._user("manager", UserRole.manager)
        self.owner = self._user("owner", manager_id=self.manager.id)
        self.outsider = self._user("outsider")
        self.other_manager = self._user("other-manager", UserRole.manager)
        self.admin = self._user("admin", UserRole.system_admin)
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
        self.indicator = Indicator(
            id="indicator-1",
            goal_id=self.goal.id,
            name="Revenue",
            direction=IndicatorDirection.positive,
            weight=1.0,
            target_value=100,
            score_method=ScoreMethod.ratio,
            redline=False,
        )

        async with self.Session() as session:
            session.add_all(
                [
                    self.manager,
                    self.owner,
                    self.outsider,
                    self.other_manager,
                    self.admin,
                    self.period,
                    self.goal,
                    self.indicator,
                ]
            )
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    @staticmethod
    def _user(
        user_id: str,
        role: UserRole = UserRole.employee,
        manager_id: str | None = None,
    ) -> User:
        return User(
            id=user_id,
            username=user_id,
            full_name=user_id,
            email=f"{user_id}@example.com",
            hashed_password="hashed",
            role=role,
            manager_id=manager_id,
        )

    async def _seed_submitted_assessment(self) -> SelfAssessment:
        assessment = SelfAssessment(
            id="assessment-1",
            goal_id=self.goal.id,
            user_id=self.owner.id,
            items={self.indicator.id: {"score": 90, "comment": "done"}},
            status=SelfAssessmentStatus.submitted,
            submitted_at=datetime.now(timezone.utc),
        )
        async with self.Session() as session:
            session.add(assessment)
            await session.commit()
        return assessment

    async def _seed_completed_evaluation(self) -> Evaluation:
        task = EvaluationTask(
            id="task-1",
            goal_id=self.goal.id,
            indicator_id=self.indicator.id,
            evaluator_user_id=self.manager.id,
            assigned_by=self.manager.id,
            status=EvaluationTaskStatus.completed,
            assigned_at=datetime.now(timezone.utc),
            due_at=datetime.now(timezone.utc),
        )
        evaluation = Evaluation(
            id="evaluation-1",
            task_id=task.id,
            goal_id=self.goal.id,
            indicator_id=self.indicator.id,
            evaluator_id=self.manager.id,
            score=88,
        )
        async with self.Session() as session:
            session.add_all([task, evaluation])
            await session.commit()
        return evaluation

    async def test_self_assessment_mutation_is_owner_only_and_reads_are_scoped(self):
        async with self.Session() as session:
            with self.assertRaises(AppException) as create_denied:
                await create_self_assessment(
                    session,
                    self.outsider,
                    self.goal.id,
                    {self.indicator.id: {"score": 80}},
                )
            self.assertEqual(create_denied.exception.status_code, 403)

            assessment = await create_self_assessment(
                session,
                self.owner,
                self.goal.id,
                {self.indicator.name: {"score": 80}},
            )
            self.assertEqual(set(assessment.items), {self.indicator.id})
            manager_view = await get_self_assessment(
                session, self.manager, assessment.id
            )
            self.assertEqual(manager_view.id, assessment.id)

            for operation in (
                lambda: get_self_assessment(session, self.outsider, assessment.id),
                lambda: get_goal_self_assessment(
                    session, self.outsider, self.goal.id
                ),
                lambda: update_self_assessment(
                    session,
                    self.outsider,
                    assessment.id,
                    {self.indicator.id: {"score": 99}},
                ),
                lambda: submit_self_assessment(
                    session, self.outsider, assessment.id
                ),
            ):
                with self.assertRaises(AppException) as denied:
                    await operation()
                self.assertEqual(denied.exception.status_code, 403)

            updated = await update_self_assessment(
                session,
                self.owner,
                assessment.id,
                {self.indicator.id: {"score": 85}},
            )
            submitted = await submit_self_assessment(
                session, self.owner, updated.id
            )
            self.assertEqual(submitted.status.value, "submitted")

    async def test_self_assessment_rejects_unknown_keys_and_incomplete_submission(self):
        async with self.Session() as session:
            with self.assertRaises(AppException) as unknown:
                await create_self_assessment(
                    session,
                    self.owner,
                    self.goal.id,
                    {"unknown-indicator": {"score": 80}},
                )
            self.assertEqual(unknown.exception.status_code, 422)

            assessment = await create_self_assessment(
                session,
                self.owner,
                self.goal.id,
                {},
            )
            assessment_id = assessment.id
            with self.assertRaises(AppException) as incomplete:
                await submit_self_assessment(session, self.owner, assessment_id)
            self.assertEqual(incomplete.exception.status_code, 422)

            await session.rollback()
            persisted = await session.get(SelfAssessment, assessment_id)
            self.assertEqual(persisted.status.value, "draft")

    async def test_historical_name_key_is_normalized_on_read(self):
        assessment = SelfAssessment(
            id="legacy-assessment",
            goal_id=self.goal.id,
            user_id=self.owner.id,
            items={self.indicator.name: {"score": 81, "comment": "legacy"}},
            status=SelfAssessmentStatus.submitted,
            submitted_at=datetime.now(timezone.utc),
        )
        async with self.Session() as session:
            session.add(assessment)
            await session.commit()

            by_id = await get_self_assessment(session, self.owner, assessment.id)
            self.assertEqual(set(by_id.items), {self.indicator.id})
            by_goal = await get_goal_self_assessment(
                session,
                self.owner,
                self.goal.id,
            )
            self.assertEqual(set(by_goal.items), {self.indicator.id})

    async def test_ambiguous_historical_name_key_is_rejected_on_read(self):
        duplicate_indicator = Indicator(
            id="indicator-duplicate-name",
            goal_id=self.goal.id,
            name=self.indicator.name,
            direction=IndicatorDirection.positive,
            weight=0,
            target_value=100,
            score_method=ScoreMethod.ratio,
            redline=False,
        )
        assessment = SelfAssessment(
            id="ambiguous-legacy-assessment",
            goal_id=self.goal.id,
            user_id=self.owner.id,
            items={self.indicator.name: {"score": 81}},
            status=SelfAssessmentStatus.submitted,
            submitted_at=datetime.now(timezone.utc),
        )
        async with self.Session() as session:
            session.add_all([duplicate_indicator, assessment])
            await session.commit()

            with self.assertRaises(AppException) as ambiguous:
                await get_self_assessment(session, self.owner, assessment.id)

        self.assertEqual(ambiguous.exception.status_code, 422)

    async def test_soft_deleted_tasks_are_hidden_from_task_lists(self):
        task = EvaluationTask(
            id="deleted-task",
            goal_id=self.goal.id,
            indicator_id=self.indicator.id,
            evaluator_user_id=self.manager.id,
            assigned_by=self.manager.id,
            assigned_at=datetime.now(timezone.utc),
            due_at=datetime.now(timezone.utc),
            status=EvaluationTaskStatus.pending,
            deleted_at=datetime.now(timezone.utc),
        )
        async with self.Session() as session:
            session.add(task)
            await session.commit()

            self.assertEqual(
                await list_evaluation_tasks(session, self.manager),
                [],
            )
            self.assertEqual(
                await get_my_pending_evaluation_tasks(session, self.manager),
                [],
            )

    async def test_evaluation_and_final_result_endpoints_reject_unrelated_users(self):
        await self._seed_submitted_assessment()
        await self._seed_completed_evaluation()

        async with self.Session() as session:
            with self.assertRaises(AppException) as task_denied:
                await generate_evaluation_tasks(
                    session, self.other_manager, self.goal.id
                )
            self.assertEqual(task_denied.exception.status_code, 403)

            for operation in (
                lambda: list_goal_evaluations(
                    session, self.outsider, self.goal.id
                ),
                lambda: generate_final_result(
                    session, self.outsider, self.goal.id
                ),
                lambda: get_final_result_by_goal(
                    session, self.outsider, self.goal.id
                ),
            ):
                with self.assertRaises(AppException) as denied:
                    await operation()
                self.assertEqual(denied.exception.status_code, 403)

            with patch("graphs.c_graph.run_c_stage", return_value={}):
                final_result = await generate_final_result(
                    session, self.owner, self.goal.id
                )

            with self.assertRaises(AppException) as get_denied:
                await get_final_result_by_goal(
                    session, self.outsider, self.goal.id
                )
            self.assertEqual(get_denied.exception.status_code, 403)

            with self.assertRaises(AppException) as confirm_denied:
                await confirm_final_result(
                    session, final_result.id, self.outsider
                )
            self.assertEqual(confirm_denied.exception.status_code, 403)

            with self.assertRaises(AppException) as owner_adjust_denied:
                await adjust_final_result(
                    session,
                    final_result.id,
                    "A",
                    "owner cannot adjust",
                    self.owner,
                )
            self.assertEqual(owner_adjust_denied.exception.status_code, 403)

            adjusted = await adjust_final_result(
                session,
                final_result.id,
                "A",
                "manager adjustment",
                self.manager,
            )
            self.assertEqual(adjusted.final_grade, "A")


if __name__ == "__main__":
    unittest.main()
