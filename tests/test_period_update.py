import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.v1.periods.schemas import PeriodResponse, PeriodUpdate
from api.v1.periods.service import update_period
from core.database import Base
from core.exceptions import (
    PeriodDateConflictError,
    PeriodStatusTransitionError,
    PermissionDeniedError,
)
from models.period import Period, PeriodStatus
from models.user import User, UserRole

# Register tables referenced by User foreign keys.
import models.organization  # noqa: F401
import models.plan_phase  # noqa: F401


class PeriodUpdateTest(unittest.IsolatedAsyncioTestCase):
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
    def _period(period_id: str, user_id: str) -> Period:
        return Period(
            id=period_id,
            user_id=user_id,
            name="Original period",
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 3, 31, tzinfo=timezone.utc),
            status=PeriodStatus.draft,
        )

    async def test_employee_cannot_update_even_their_own_period(self):
        employee = self._user("employee-1")
        period = self._period("period-1", employee.id)

        async with self.Session() as session:
            session.add_all([employee, period])
            await session.commit()

            with self.assertRaises(PermissionDeniedError):
                await update_period(
                    session,
                    employee,
                    period.id,
                    {"name": "Employee edit"},
                )

    async def test_manager_can_update_own_and_recursive_subordinate_periods(self):
        manager = self._user("manager-1", UserRole.manager)
        team_lead = self._user("manager-2", UserRole.manager, manager.id)
        employee = self._user("employee-1", manager_id=team_lead.id)
        own_period = self._period("period-manager", manager.id)
        subordinate_period = self._period("period-employee", employee.id)

        async with self.Session() as session:
            session.add_all(
                [manager, team_lead, employee, own_period, subordinate_period]
            )
            await session.commit()

            updated_own = await update_period(
                session,
                manager,
                own_period.id,
                {"name": "Manager period"},
            )
            updated_subordinate = await update_period(
                session,
                manager,
                subordinate_period.id,
                {"name": "Employee period"},
            )

        self.assertEqual(updated_own.name, "Manager period")
        self.assertEqual(updated_subordinate.name, "Employee period")

    async def test_manager_cannot_update_unrelated_users_period(self):
        manager = self._user("manager-1", UserRole.manager)
        unrelated_employee = self._user("employee-1")
        period = self._period("period-1", unrelated_employee.id)

        async with self.Session() as session:
            session.add_all([manager, unrelated_employee, period])
            await session.commit()

            with self.assertRaises(PermissionDeniedError):
                await update_period(
                    session,
                    manager,
                    period.id,
                    {"name": "Out of scope"},
                )

    async def test_manager_cannot_update_soft_deleted_subordinates_period(self):
        manager = self._user("manager-1", UserRole.manager)
        deleted_employee = self._user("employee-1", manager_id=manager.id)
        deleted_employee.deleted_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        period = self._period("period-1", deleted_employee.id)

        async with self.Session() as session:
            session.add_all([manager, deleted_employee, period])
            await session.commit()

            with self.assertRaises(PermissionDeniedError):
                await update_period(
                    session,
                    manager,
                    period.id,
                    {"name": "Deleted subordinate"},
                )

    async def test_manager_hierarchy_cycle_terminates_and_keeps_descendant_scope(self):
        manager = self._user("manager-1", UserRole.manager, "manager-3")
        team_lead = self._user("manager-2", UserRole.manager, manager.id)
        nested_manager = self._user("manager-3", UserRole.manager, team_lead.id)
        period = self._period("period-1", nested_manager.id)

        async with self.Session() as session:
            session.add_all([manager, team_lead, nested_manager, period])
            await session.commit()

            progress_calls = 0

            def stop_runaway_recursion() -> int:
                nonlocal progress_calls
                progress_calls += 1
                return int(progress_calls > 10_000)

            connection = await session.connection()
            raw_connection = await connection.get_raw_connection()
            driver_connection = raw_connection.driver_connection
            await driver_connection.set_progress_handler(
                stop_runaway_recursion,
                100,
            )
            try:
                updated = await update_period(
                    session,
                    manager,
                    period.id,
                    {"name": "Cycle-safe edit"},
                )
            finally:
                await driver_connection.set_progress_handler(None, 0)

        self.assertEqual(updated.name, "Cycle-safe edit")

    async def test_hr_and_system_admins_can_update_any_period(self):
        employee = self._user("employee-1")
        hr_admin = self._user("hr-1", UserRole.hr_admin)
        system_admin = self._user("admin-1", UserRole.system_admin)
        hr_period = self._period("period-hr", employee.id)
        system_period = self._period("period-system", employee.id)

        async with self.Session() as session:
            session.add_all(
                [employee, hr_admin, system_admin, hr_period, system_period]
            )
            await session.commit()

            updated_by_hr = await update_period(
                session,
                hr_admin,
                hr_period.id,
                {"name": "HR edit"},
            )
            updated_by_system = await update_period(
                session,
                system_admin,
                system_period.id,
                {"name": "System edit"},
            )

        self.assertEqual(updated_by_hr.name, "HR edit")
        self.assertEqual(updated_by_system.name, "System edit")

    def test_update_schema_only_accepts_name_and_date_fields(self):
        allowed = PeriodUpdate.model_validate(
            {
                "name": "Updated period",
                "start_date": "2026-04-01T00:00:00Z",
                "end_date": "2026-06-30T00:00:00Z",
            }
        )
        self.assertEqual(allowed.name, "Updated period")

        for forbidden_field, value in (
            ("description", "Not editable"),
            ("user_id", "employee-2"),
            ("status", "closed"),
        ):
            with self.subTest(field=forbidden_field):
                with self.assertRaises(ValidationError):
                    PeriodUpdate.model_validate({forbidden_field: value})

    async def test_closed_and_archived_periods_cannot_be_updated(self):
        admin = self._user("admin-1", UserRole.system_admin)
        closed_period = self._period("period-closed", "employee-1")
        closed_period.status = PeriodStatus.closed
        archived_period = self._period("period-archived", "employee-1")
        archived_period.status = PeriodStatus.archived

        async with self.Session() as session:
            session.add_all([admin, closed_period, archived_period])
            await session.commit()

            for period in (closed_period, archived_period):
                with self.subTest(status=period.status):
                    with self.assertRaises(PeriodStatusTransitionError):
                        await update_period(
                            session,
                            admin,
                            period.id,
                            {"name": "Should not change"},
                        )

    async def test_open_period_can_update_name_and_dates(self):
        admin = self._user("admin-1", UserRole.system_admin)
        period = self._period("period-1", "employee-1")
        period.status = PeriodStatus.open
        period.description = "Existing description"
        new_start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        new_end = datetime(2026, 6, 30, tzinfo=timezone.utc)

        async with self.Session() as session:
            session.add_all([admin, period])
            await session.commit()

            updated = await update_period(
                session,
                admin,
                period.id,
                {
                    "name": "Open period",
                    "start_date": new_start,
                    "end_date": new_end,
                },
            )

        self.assertEqual(updated.name, "Open period")
        self.assertEqual(updated.start_date.replace(tzinfo=timezone.utc), new_start)
        self.assertEqual(updated.end_date.replace(tzinfo=timezone.utc), new_end)
        response = PeriodResponse.model_validate(updated).model_dump(mode="json")
        self.assertEqual(
            set(response),
            {
                "id",
                "user_id",
                "name",
                "start_date",
                "end_date",
                "status",
                "d_phase_completed",
                "description",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual(response["description"], "Existing description")

    async def test_partial_start_date_update_is_validated_against_current_end_date(self):
        admin = self._user("admin-1", UserRole.system_admin)
        period = self._period("period-1", "employee-1")
        original_start = period.start_date

        async with self.Session() as session:
            session.add_all([admin, period])
            await session.commit()

            with self.assertRaises(PeriodDateConflictError):
                await update_period(
                    session,
                    admin,
                    period.id,
                    {"start_date": datetime(2026, 4, 1, tzinfo=timezone.utc)},
                )

            await session.refresh(period)

        self.assertEqual(period.start_date.replace(tzinfo=timezone.utc), original_start)

    async def test_later_partial_patch_cannot_create_an_invalid_date_range(self):
        admin = self._user("admin-1", UserRole.system_admin)
        period = self._period("period-1", "employee-1")
        period.end_date = datetime(2026, 12, 31, tzinfo=timezone.utc)
        valid_start = datetime(2026, 11, 1, tzinfo=timezone.utc)
        original_end = period.end_date

        async with self.Session() as session:
            session.add_all([admin, period])
            await session.commit()

            await update_period(
                session,
                admin,
                period.id,
                {"start_date": valid_start},
            )

            with self.assertRaises(PeriodDateConflictError):
                await update_period(
                    session,
                    admin,
                    period.id,
                    {"end_date": datetime(2026, 2, 1, tzinfo=timezone.utc)},
                )

            await session.refresh(period)

        self.assertEqual(period.start_date.replace(tzinfo=timezone.utc), valid_start)
        self.assertEqual(period.end_date.replace(tzinfo=timezone.utc), original_end)

    async def test_start_date_must_be_strictly_before_end_date(self):
        admin = self._user("admin-1", UserRole.system_admin)
        period = self._period("period-1", "employee-1")
        same_date = datetime(2026, 2, 1, tzinfo=timezone.utc)

        async with self.Session() as session:
            session.add_all([admin, period])
            await session.commit()

            with self.assertRaises(PeriodDateConflictError):
                await update_period(
                    session,
                    admin,
                    period.id,
                    {"start_date": same_date, "end_date": same_date},
                )


class PeriodUpdateConcurrencyTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name, "period-update.db").as_posix()
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{database_path}",
            connect_args={"timeout": 5},
        )
        self.Session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()
        self.temp_dir.cleanup()

    @staticmethod
    def _admin() -> User:
        return User(
            id="admin-1",
            username="admin-1",
            full_name="admin-1",
            email="admin-1@example.com",
            hashed_password="hashed",
            role=UserRole.system_admin,
        )

    @staticmethod
    def _period() -> Period:
        return Period(
            id="period-1",
            user_id="employee-1",
            name="Original period",
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 12, 31, tzinfo=timezone.utc),
            status=PeriodStatus.open,
        )

    async def _seed(self) -> User:
        admin = self._admin()
        async with self.Session() as session:
            session.add_all([admin, self._period()])
            await session.commit()
        return admin

    async def test_sqlite_update_starts_with_begin_immediate(self):
        admin = await self._seed()
        statements: list[str] = []

        def record_statement(
            _conn,
            _cursor,
            statement,
            _parameters,
            _context,
            _executemany,
        ):
            statements.append(statement.strip())

        event.listen(self.engine.sync_engine, "before_cursor_execute", record_statement)
        try:
            async with self.Session() as session:
                await update_period(
                    session,
                    admin,
                    "period-1",
                    {"name": "Serialized update"},
                )
        finally:
            event.remove(
                self.engine.sync_engine,
                "before_cursor_execute",
                record_statement,
            )

        self.assertTrue(statements)
        self.assertEqual(statements[0].upper(), "BEGIN IMMEDIATE")

    async def test_sqlite_lock_setup_does_not_commit_unrelated_session_changes(self):
        admin = await self._seed()

        async with self.Session() as session:
            session_admin = await session.get(User, admin.id)
            self.assertIsNotNone(session_admin)
            session_admin.full_name = "Must not be committed"

            with self.assertRaisesRegex(RuntimeError, "pending session changes"):
                await update_period(
                    session,
                    session_admin,
                    "period-1",
                    {"name": "Serialized update"},
                )

        async with self.Session() as verification_session:
            persisted_admin = await verification_session.get(User, admin.id)

        self.assertIsNotNone(persisted_admin)
        self.assertEqual(persisted_admin.full_name, "admin-1")

    async def test_concurrent_partial_updates_cannot_persist_invalid_dates(self):
        admin = await self._seed()

        async with self.Session() as start_session, self.Session() as end_session:
            start_snapshot = await start_session.get(Period, "period-1")
            end_snapshot = await end_session.get(Period, "period-1")
            await start_session.commit()
            await end_session.commit()
            self.assertIsNotNone(start_snapshot)
            self.assertIsNotNone(end_snapshot)

            results = await asyncio.gather(
                update_period(
                    start_session,
                    admin,
                    "period-1",
                    {"start_date": datetime(2026, 11, 1, tzinfo=timezone.utc)},
                ),
                update_period(
                    end_session,
                    admin,
                    "period-1",
                    {"end_date": datetime(2026, 2, 1, tzinfo=timezone.utc)},
                ),
                return_exceptions=True,
            )

        successful_updates = [result for result in results if isinstance(result, Period)]
        conflicts = [
            result for result in results if isinstance(result, PeriodDateConflictError)
        ]
        self.assertEqual(len(successful_updates), 1, results)
        self.assertEqual(len(conflicts), 1, results)

        async with self.Session() as session:
            persisted = await session.get(Period, "period-1")

        self.assertIsNotNone(persisted)
        self.assertLess(
            persisted.start_date.replace(tzinfo=timezone.utc),
            persisted.end_date.replace(tzinfo=timezone.utc),
        )


if __name__ == "__main__":
    unittest.main()
