import unittest
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.v1.action import service
from core.database import Base
from core.exceptions import PermissionDeniedError
from models.action_phase import DevelopmentPlan, InheritanceSuggestion, ReviewReport
from models.check_phase import FinalResult, FinalResultStatus, Goal
from models.period import Period, PeriodStatus
from models.user import User, UserRole

# Register every table referenced by the metadata's foreign keys.
import models.organization  # noqa: F401
import models.plan_phase  # noqa: F401


class ActionObjectPermissionsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.Session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        now = datetime.now(timezone.utc)
        self.manager = User(
            id="manager",
            username="manager",
            full_name="Manager",
            email="manager@example.com",
            hashed_password="hashed",
            role=UserRole.manager,
        )
        self.owner = User(
            id="owner",
            username="owner",
            full_name="Owner",
            email="owner@example.com",
            hashed_password="hashed",
            role=UserRole.employee,
            manager_id=self.manager.id,
        )
        self.outsider = User(
            id="outsider",
            username="outsider",
            full_name="Outsider",
            email="outsider@example.com",
            hashed_password="hashed",
            role=UserRole.employee,
        )
        self.period = Period(
            id="period",
            user_id=self.owner.id,
            name="Period",
            start_date=now,
            end_date=now,
            status=PeriodStatus.closed,
        )
        self.next_period = Period(
            id="next-period",
            user_id=self.owner.id,
            name="Next period",
            start_date=now,
            end_date=now,
            status=PeriodStatus.draft,
        )
        self.goal = Goal(
            id="goal",
            owner_user_id=self.owner.id,
            period_id=self.period.id,
            title="Goal",
            created_by=self.owner.id,
        )
        self.final_result = FinalResult(
            id="final-result",
            goal_id=self.goal.id,
            final_grade="B",
            confirmed_by=self.manager.id,
            confirmed_at=now,
            status=FinalResultStatus.confirmed,
        )
        self.report = ReviewReport(
            id="report",
            final_result_id=self.final_result.id,
            user_id=self.owner.id,
            report_type="b",
            strengths_analysis={},
            improvement_areas={"areas": []},
            ai_generated=True,
            generated_at=now,
        )
        self.plan = DevelopmentPlan(
            id="plan",
            review_report_id=self.report.id,
            user_id=self.owner.id,
            goals={"text": "Original"},
            actions={"text": "Original"},
            status="draft",
        )
        self.suggestion = InheritanceSuggestion(
            id="suggestion",
            user_id=self.owner.id,
            previous_development_plan_id=self.plan.id,
            previous_final_result_id=self.final_result.id,
            new_period_id=self.next_period.id,
            suggestion_type="new_indicator",
            suggestions={"summary": "Carry forward"},
            status="pending",
        )

        async with self.Session() as session:
            session.add_all([
                self.manager,
                self.owner,
                self.outsider,
                self.period,
                self.next_period,
                self.goal,
                self.final_result,
                self.report,
                self.plan,
                self.suggestion,
            ])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_outsider_cannot_read_action_objects_even_when_ids_are_known(self):
        async with self.Session() as session:
            with self.assertRaises(PermissionDeniedError):
                await service.generate_review_report(
                    session,
                    self.outsider,
                    self.final_result.id,
                )
            with self.assertRaises(PermissionDeniedError):
                await service.get_review_report(session, self.outsider, self.report.id)
            with self.assertRaises(PermissionDeniedError):
                await service.get_development_plan(session, self.outsider, self.plan.id)
            with self.assertRaises(PermissionDeniedError):
                await service.get_inheritance_suggestion(
                    session,
                    self.outsider,
                    self.suggestion.id,
                )

            self.assertEqual(
                (await service.get_review_report(session, self.manager, self.report.id)).id,
                self.report.id,
            )

    async def test_only_owner_mutates_plan_and_inheritance_but_manager_can_approve(self):
        async with self.Session() as session:
            with self.assertRaises(PermissionDeniedError):
                await service.update_development_plan(
                    session,
                    self.outsider,
                    self.plan.id,
                    {"goals": {"text": "Hijacked"}},
                )
            with self.assertRaises(PermissionDeniedError):
                await service.accept_suggestion(
                    session,
                    self.outsider,
                    self.suggestion.id,
                )
            with self.assertRaises(PermissionDeniedError):
                await service.approve_plan(
                    session,
                    self.owner,
                    self.plan.id,
                    True,
                )

            updated = await service.update_development_plan(
                session,
                self.owner,
                self.plan.id,
                {"goals": {"text": "Owner edit"}},
            )
            self.assertEqual(updated.goals, {"text": "Owner edit"})

            approved = await service.approve_plan(
                session,
                self.manager,
                self.plan.id,
                True,
            )
            self.assertEqual(approved.status.value, "approved")

            accepted = await service.accept_suggestion(
                session,
                self.owner,
                self.suggestion.id,
            )
            self.assertEqual(accepted.status.value, "accepted")


if __name__ == "__main__":
    unittest.main()
