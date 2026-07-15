import unittest
from datetime import date, datetime, timezone

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.v1.periods.schemas import PeriodHistoryResponse
from api.v1.periods.service import list_period_history
from core.database import Base
from core.exceptions import UserAccessDeniedError, UserNotFoundError
from models.check_phase import FinalResult, FinalResultStatus, Goal
from models.do_phase import DiagnosticReport, TrafficLightStatus
from models.period import Period, PeriodStatus
from models.user import User, UserRole

# Import models with foreign keys referenced by the tables under test.
import models.organization  # noqa: F401
import models.plan_phase  # noqa: F401


class PeriodHistoryTest(unittest.IsolatedAsyncioTestCase):
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

    @staticmethod
    def _period(
        period_id: str,
        user_id: str,
        end_date: datetime,
        status: PeriodStatus,
    ) -> Period:
        return Period(
            id=period_id,
            user_id=user_id,
            name=period_id,
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=end_date,
            status=status,
        )

    @staticmethod
    def _goal(goal_id: str, user_id: str, period_id: str) -> Goal:
        return Goal(
            id=goal_id,
            owner_user_id=user_id,
            period_id=period_id,
            title=goal_id,
            created_by=user_id,
        )

    @staticmethod
    def _diagnostic(
        report_id: str,
        goal_id: str,
        user_id: str,
        created_at: datetime,
    ) -> DiagnosticReport:
        return DiagnosticReport(
            id=report_id,
            goal_id=goal_id,
            user_id=user_id,
            report_date=date(2026, 6, 30),
            overall_progress=80,
            weighted_achievement_rate=85,
            time_progress=75,
            progress_deviation=10,
            traffic_light_status=TrafficLightStatus.green,
            created_at=created_at,
        )

    async def test_self_history_only_includes_closed_and_archived_in_stable_order(self):
        employee = self._user("employee-1")
        same_end_date = datetime(2026, 6, 30, tzinfo=timezone.utc)
        session_end_date = datetime(2026, 3, 31, tzinfo=timezone.utc)
        deleted_period = self._period(
            "period-deleted",
            employee.id,
            datetime(2026, 9, 30, tzinfo=timezone.utc),
            PeriodStatus.closed,
        )
        deleted_period.deleted_at = datetime(2026, 10, 1, tzinfo=timezone.utc)
        periods = [
            self._period("period-a", employee.id, same_end_date, PeriodStatus.closed),
            self._period("period-b", employee.id, same_end_date, PeriodStatus.archived),
            self._period("period-old", employee.id, session_end_date, PeriodStatus.closed),
            self._period("period-draft", employee.id, same_end_date, PeriodStatus.draft),
            deleted_period,
            self._period(
                "period-open",
                employee.id,
                datetime(2026, 12, 31, tzinfo=timezone.utc),
                PeriodStatus.open,
            ),
        ]

        async with self.Session() as session:
            session.add_all([employee, *periods])
            await session.commit()

            history = await list_period_history(session, employee, page=1, limit=2)

        self.assertEqual(
            [item["period_id"] for item in history["items"]],
            ["period-b", "period-a"],
        )
        self.assertEqual(history["total"], 3)
        self.assertEqual(history["page"], 1)
        self.assertEqual(history["page_size"], 2)

        async with self.Session() as session:
            second_page = await list_period_history(session, employee, page=2, limit=2)

        self.assertEqual(
            [item["period_id"] for item in second_page["items"]],
            ["period-old"],
        )

        async with self.Session() as session:
            empty_page = await list_period_history(session, employee, page=99, limit=2)

        self.assertEqual(empty_page["items"], [])
        self.assertEqual(empty_page["total"], 3)
        self.assertEqual(empty_page["page"], 99)

    async def test_period_without_goal_is_still_returned(self):
        employee = self._user("employee-1")
        period = self._period(
            "period-without-goal",
            employee.id,
            datetime(2026, 3, 31, tzinfo=timezone.utc),
            PeriodStatus.closed,
        )

        async with self.Session() as session:
            session.add_all([employee, period])
            await session.commit()

            history = await list_period_history(session, employee)

        self.assertEqual(len(history["items"]), 1)
        self.assertEqual(history["items"][0]["period_id"], period.id)
        self.assertIsNone(history["items"][0]["goal_id"])
        self.assertIsNone(history["items"][0]["diagnostic_summary"])
        self.assertFalse(history["items"][0]["has_data_conflict"])

    async def test_latest_diagnostic_uses_id_as_tiebreaker_for_equal_created_at(self):
        employee = self._user("employee-1")
        period = self._period(
            "period-1",
            employee.id,
            datetime(2026, 6, 30, tzinfo=timezone.utc),
            PeriodStatus.closed,
        )
        goal = self._goal("goal-1", employee.id, period.id)
        same_created_at = datetime(2026, 6, 30, 12, tzinfo=timezone.utc)
        diagnostics = [
            self._diagnostic("diagnostic-a", goal.id, employee.id, same_created_at),
            self._diagnostic("diagnostic-b", goal.id, employee.id, same_created_at),
        ]
        final_result = FinalResult(
            id="final-result-1",
            goal_id=goal.id,
            final_grade="A",
            confirmed_by=employee.id,
            confirmed_at=same_created_at,
            status=FinalResultStatus.confirmed,
        )

        async with self.Session() as session:
            session.add_all([employee, period, goal, *diagnostics, final_result])
            await session.commit()

            history = await list_period_history(session, employee)

        item = history["items"][0]
        self.assertEqual(item["diagnostic_summary"]["id"], "diagnostic-b")
        self.assertEqual(item["final_result_summary"]["final_grade"], "A")
        serialized = PeriodHistoryResponse.model_validate(history).model_dump(mode="json")
        self.assertEqual(serialized["items"][0]["status"], "closed")
        self.assertEqual(
            serialized["items"][0]["diagnostic_summary"]["traffic_light_status"],
            "green",
        )
        self.assertEqual(
            serialized["items"][0]["final_result_summary"]["status"],
            "confirmed",
        )

    async def test_soft_deleted_final_result_is_not_returned(self):
        employee = self._user("employee-1")
        period = self._period(
            "period-1",
            employee.id,
            datetime(2026, 6, 30, tzinfo=timezone.utc),
            PeriodStatus.closed,
        )
        goal = self._goal("goal-1", employee.id, period.id)
        deleted_result = FinalResult(
            id="final-result-deleted",
            goal_id=goal.id,
            final_grade="A",
            confirmed_by=employee.id,
            confirmed_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
            status=FinalResultStatus.confirmed,
            deleted_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        )

        async with self.Session() as session:
            session.add_all([employee, period, goal, deleted_result])
            await session.commit()

            history = await list_period_history(session, employee)

        self.assertIsNone(history["items"][0]["final_result_summary"])

    async def test_duplicate_goals_report_conflict_without_diagnostic_summary(self):
        employee = self._user("employee-1")
        period = self._period(
            "period-1",
            employee.id,
            datetime(2026, 6, 30, tzinfo=timezone.utc),
            PeriodStatus.closed,
        )
        goals = [
            self._goal("goal-a", employee.id, period.id),
            self._goal("goal-b", employee.id, period.id),
        ]
        diagnostics = [
            self._diagnostic(
                "diagnostic-a",
                goals[0].id,
                employee.id,
                datetime(2026, 6, 29, tzinfo=timezone.utc),
            ),
            self._diagnostic(
                "diagnostic-b",
                goals[1].id,
                employee.id,
                datetime(2026, 6, 30, tzinfo=timezone.utc),
            ),
        ]

        async with self.Session() as session:
            session.add_all([employee, period, *goals, *diagnostics])
            await session.commit()

            history = await list_period_history(session, employee)

        self.assertEqual(len(history["items"]), 1)
        self.assertTrue(history["items"][0]["has_data_conflict"])
        self.assertIsNone(history["items"][0]["goal_id"])
        self.assertIsNone(history["items"][0]["diagnostic_summary"])

    async def test_goal_owned_by_another_user_is_not_used_for_summary(self):
        employee = self._user("employee-1")
        other_employee = self._user("employee-2")
        period = self._period(
            "period-1",
            employee.id,
            datetime(2026, 6, 30, tzinfo=timezone.utc),
            PeriodStatus.closed,
        )
        mismatched_goal = self._goal("goal-1", other_employee.id, period.id)

        async with self.Session() as session:
            session.add_all([employee, other_employee, period, mismatched_goal])
            await session.commit()

            history = await list_period_history(session, employee)

        self.assertIsNone(history["items"][0]["goal_id"])
        self.assertFalse(history["items"][0]["has_data_conflict"])

    async def test_employee_cannot_access_another_users_history(self):
        employee = self._user("employee-1")
        other_employee = self._user("employee-2")

        async with self.Session() as session:
            session.add_all([employee, other_employee])
            await session.commit()

            with self.assertRaises(UserAccessDeniedError):
                await list_period_history(session, employee, other_employee.id)

    async def test_manager_can_access_direct_reports_history(self):
        manager = self._user("manager-1", role=UserRole.manager)
        employee = self._user("employee-1", manager_id=manager.id)
        period = self._period(
            "period-1",
            employee.id,
            datetime(2026, 6, 30, tzinfo=timezone.utc),
            PeriodStatus.closed,
        )

        async with self.Session() as session:
            session.add_all([manager, employee, period])
            await session.commit()

            history = await list_period_history(session, manager, employee.id)

        self.assertEqual([item["period_id"] for item in history["items"]], [period.id])

    async def test_manager_history_query_count_is_constant_for_deep_hierarchy(self):
        manager = self._user("manager-1", role=UserRole.manager)
        team_lead = self._user(
            "manager-2",
            role=UserRole.manager,
            manager_id=manager.id,
        )
        employee = self._user("employee-1", manager_id=team_lead.id)
        period = self._period(
            "period-1",
            employee.id,
            datetime(2026, 6, 30, tzinfo=timezone.utc),
            PeriodStatus.closed,
        )

        async with self.Session() as session:
            session.add_all([manager, team_lead, employee, period])
            await session.commit()

            select_count = 0

            def count_selects(_conn, _cursor, statement, _parameters, _context, _many):
                nonlocal select_count
                if statement.lstrip().upper().startswith(("SELECT", "WITH RECURSIVE")):
                    select_count += 1

            event.listen(
                self.engine.sync_engine,
                "before_cursor_execute",
                count_selects,
            )
            try:
                history = await list_period_history(session, manager, employee.id)
            finally:
                event.remove(
                    self.engine.sync_engine,
                    "before_cursor_execute",
                    count_selects,
                )

        self.assertEqual([item["period_id"] for item in history["items"]], [period.id])
        self.assertLessEqual(select_count, 7)

    async def test_admin_cannot_query_missing_or_soft_deleted_user(self):
        admin = self._user("admin-1", role=UserRole.system_admin)
        deleted_user = self._user("employee-deleted")
        deleted_user.deleted_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

        async with self.Session() as session:
            session.add_all([admin, deleted_user])
            await session.commit()

            with self.assertRaises(UserNotFoundError):
                await list_period_history(session, admin, "missing-user")
            with self.assertRaises(UserNotFoundError):
                await list_period_history(session, admin, deleted_user.id)


if __name__ == "__main__":
    unittest.main()
