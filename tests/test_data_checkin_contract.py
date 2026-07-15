import math
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.v1.do.schemas import DataCheckinCreate
from api.v1.do.service import (
    create_coaching_request,
    generate_diagnostic_report,
    get_checkin,
    get_coaching_request,
    get_diagnostic_report,
    get_goal_by_user,
    get_latest_report,
    list_indicator_checkins,
    list_goal_indicators,
    list_goal_reports,
    submit_checkin,
    update_request_status,
    update_checkin,
)
from core.database import Base
from core.exceptions import AppException, PeriodNotOpenError
from models.check_phase import Goal, Indicator, IndicatorDirection, ScoreMethod
from models.do_phase import DataCheckin, DiagnosticReport
from models.period import Period, PeriodStatus
from models.plan_phase import PerformanceContract
from models.user import User, UserRole
from utils.calculations import calculate_d_stage

# Import tables referenced by foreign keys in the test schema.
import models.action_phase  # noqa: F401
import models.organization  # noqa: F401


@pytest.mark.parametrize(
    ("actual_value", "expected"),
    [
        (
            {"value_type": "quantitative", "value": 12.5},
            {"value_type": "quantitative", "value": 12.5},
        ),
        (
            {"value_type": "qualitative", "value": "in_progress"},
            {"value_type": "qualitative", "value": "in_progress"},
        ),
        (
            {"value_type": "redline", "value": 2},
            {"value_type": "redline", "value": 2},
        ),
    ],
)
def test_data_checkin_request_uses_discriminated_value_contract(actual_value, expected):
    payload = DataCheckinCreate(indicator_id="indicator-1", actual_value=actual_value)

    assert payload.actual_value.model_dump() == expected


@pytest.mark.parametrize(
    "actual_value",
    [
        {"value": 12},
        {"value_type": "quantitative", "value": math.inf},
        {"value_type": "quantitative", "value": "12"},
        {"value_type": "qualitative", "value": "almost_done"},
        {"value_type": "redline", "value": -1},
        {"value_type": "redline", "value": 1.5},
        {"value_type": "redline", "value": True},
        {"value_type": "redline", "value": 1, "unit": "times"},
    ],
)
def test_data_checkin_request_rejects_values_outside_fixed_contract(actual_value):
    with pytest.raises(ValidationError):
        DataCheckinCreate(indicator_id="indicator-1", actual_value=actual_value)


def test_data_checkin_request_rejects_unknown_outer_fields():
    with pytest.raises(ValidationError):
        DataCheckinCreate(
            indicator_id="indicator-1",
            actual_value={"value_type": "quantitative", "value": 12},
            task_id="legacy-task",
        )


def test_d_stage_uses_indicator_ids_when_display_names_collide():
    result = calculate_d_stage(
        [
            {
                "indicator_id": "indicator-1",
                "name": "Same name",
                "type": "positive",
                "target": 100,
                "weight": 50,
            },
            {
                "indicator_id": "indicator-2",
                "name": "Same name",
                "type": "positive",
                "target": 100,
                "weight": 50,
            },
        ],
        {"indicator-1": 50, "indicator-2": 100},
    )

    by_id = {
        item["indicator_id"]: item
        for item in result["indicator_results"]
    }
    assert by_id["indicator-1"]["actual_value"] == 50
    assert by_id["indicator-2"]["actual_value"] == 100
    assert result["weighted_achievement"] == 75


class DataCheckinServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.Session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.owner = self._user("owner", manager_id="team-lead")
        self.team_lead = self._user("team-lead", UserRole.manager, "manager")
        self.manager = self._user("manager", UserRole.manager)
        self.outsider = self._user("outsider")
        self.admin = self._user("admin", UserRole.system_admin)
        self.period = Period(
            id="period-1",
            user_id=self.owner.id,
            name="Open period",
            start_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 7, 31, tzinfo=timezone.utc),
            status=PeriodStatus.open,
        )
        self.contract = PerformanceContract(
            id="contract-1",
            job_prototype_code="S",
            strategy_config={},
            contract_data={
                "indicators": [
                    {"name": "Revenue", "type": "positive"},
                    {"name": "Delivery", "type": "qualitative"},
                    {"name": "Incidents", "type": "redline"},
                ]
            },
        )
        self.goal = Goal(
            id="goal-1",
            owner_user_id=self.owner.id,
            period_id=self.period.id,
            title="Goal",
            created_by=self.owner.id,
            performance_contract_id=self.contract.id,
        )
        self.quantitative = self._indicator(
            "indicator-quantitative", "Revenue", IndicatorDirection.positive, 1.0
        )
        self.qualitative = self._indicator(
            "indicator-qualitative", "Delivery", IndicatorDirection.positive, 0.0
        )
        self.qualitative.score_method = ScoreMethod.manual
        self.redline = self._indicator(
            "indicator-redline", "Incidents", IndicatorDirection.negative, 0.0, redline=True
        )
        self.redline.score_method = ScoreMethod.binary

        async with self.Session() as session:
            session.add_all(
                [
                    self.owner,
                    self.team_lead,
                    self.manager,
                    self.outsider,
                    self.admin,
                    self.period,
                    self.contract,
                    self.goal,
                    self.quantitative,
                    self.qualitative,
                    self.redline,
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

    def _indicator(
        self,
        indicator_id: str,
        name: str,
        direction: IndicatorDirection,
        weight: float,
        redline: bool = False,
    ) -> Indicator:
        return Indicator(
            id=indicator_id,
            goal_id=self.goal.id,
            name=name,
            direction=direction,
            weight=weight,
            target_value=100,
            score_method=ScoreMethod.ratio,
            redline=redline,
        )

    async def test_persists_canonical_value_and_validates_indicator_type(self):
        async with self.Session() as session:
            checkin = await submit_checkin(
                session,
                self.owner,
                self.quantitative.id,
                {"value_type": "quantitative", "value": 42.5},
            )

            self.assertEqual(
                checkin.actual_value,
                {"value_type": "quantitative", "value": 42.5},
            )

            with self.assertRaises(AppException) as mismatch:
                await submit_checkin(
                    session,
                    self.owner,
                    self.quantitative.id,
                    {"value_type": "qualitative", "value": "completed"},
                )
            self.assertEqual(mismatch.exception.status_code, 422)

    async def test_duplicate_contract_names_cannot_override_persisted_indicator_type(self):
        async with self.Session() as session:
            contract = await session.get(PerformanceContract, self.contract.id)
            contract.contract_data = {
                "indicators": [
                    {"name": "Revenue", "type": "positive"},
                    {"name": "Revenue", "type": "qualitative"},
                ]
            }
            await session.commit()

            checkin = await submit_checkin(
                session,
                self.owner,
                self.quantitative.id,
                {"value_type": "quantitative", "value": 42},
            )
            indicators = await list_goal_indicators(
                session, self.owner, self.goal.id
            )

        self.assertEqual(checkin.actual_value["value_type"], "quantitative")
        by_id = {indicator["id"]: indicator for indicator in indicators}
        self.assertEqual(
            by_id[self.quantitative.id]["indicator_type"], "positive"
        )
        self.assertIsNone(by_id[self.quantitative.id]["unit"])

    async def test_closed_period_checkin_cannot_be_updated(self):
        async with self.Session() as session:
            checkin = await submit_checkin(
                session,
                self.owner,
                self.redline.id,
                {"value_type": "redline", "value": 0},
            )
            period = await session.get(Period, self.period.id)
            period.status = PeriodStatus.closed
            await session.commit()

            with self.assertRaises(PeriodNotOpenError):
                await update_checkin(
                    session,
                    self.owner,
                    checkin.id,
                    {"value_type": "redline", "value": 1},
                )

    async def test_owner_recursive_manager_and_admin_can_access_checkin(self):
        async with self.Session() as session:
            created = await submit_checkin(
                session,
                self.owner,
                self.quantitative.id,
                {"value_type": "quantitative", "value": 10},
            )

        async with self.Session() as session:
            manager_view = await get_checkin(session, self.manager, created.id)
            self.assertEqual(manager_view.id, created.id)

            updated = await update_checkin(
                session,
                self.manager,
                created.id,
                {"value_type": "quantitative", "value": 11},
            )
            self.assertEqual(updated.actual_value["value"], 11)

            listed = await list_indicator_checkins(
                session, self.admin, self.quantitative.id
            )
            self.assertEqual([item.id for item in listed], [created.id])

    async def test_recursive_manager_access_terminates_when_hierarchy_has_a_cycle(self):
        async with self.Session() as session:
            manager = await session.get(User, self.manager.id)
            manager.manager_id = self.owner.id
            await session.commit()

            connection = await session.connection()
            raw_connection = await connection.get_raw_connection()
            driver_connection = raw_connection.driver_connection
            progress_calls = 0

            def stop_runaway_recursion() -> int:
                nonlocal progress_calls
                progress_calls += 1
                return int(progress_calls > 10_000)

            await driver_connection.set_progress_handler(stop_runaway_recursion, 100)
            try:
                checkin = await submit_checkin(
                    session,
                    self.manager,
                    self.quantitative.id,
                    {"value_type": "quantitative", "value": 12},
                )
            finally:
                await driver_connection.set_progress_handler(None, 0)

        self.assertEqual(checkin.indicator_id, self.quantitative.id)

    async def test_outsider_cannot_create_read_update_or_list_checkins(self):
        async with self.Session() as session:
            created = await submit_checkin(
                session,
                self.owner,
                self.quantitative.id,
                {"value_type": "quantitative", "value": 10},
            )

            operations = [
                lambda: submit_checkin(
                    session,
                    self.outsider,
                    self.quantitative.id,
                    {"value_type": "quantitative", "value": 11},
                ),
                lambda: get_checkin(session, self.outsider, created.id),
                lambda: update_checkin(
                    session,
                    self.outsider,
                    created.id,
                    {"value_type": "quantitative", "value": 12},
                ),
                lambda: list_indicator_checkins(
                    session, self.outsider, self.quantitative.id
                ),
            ]
            for operation in operations:
                with self.assertRaises(AppException) as denied:
                    await operation()
                self.assertEqual(denied.exception.status_code, 403)

    async def test_soft_deleted_indicator_or_goal_makes_checkin_unavailable(self):
        async with self.Session() as session:
            created = await submit_checkin(
                session,
                self.owner,
                self.quantitative.id,
                {"value_type": "quantitative", "value": 10},
            )
            indicator = await session.get(Indicator, self.quantitative.id)
            indicator.deleted_at = datetime.now(timezone.utc)
            await session.commit()

        async with self.Session() as session:
            with self.assertRaises(AppException) as missing:
                await get_checkin(session, self.owner, created.id)
            self.assertEqual(missing.exception.status_code, 404)

    async def test_diagnostic_reads_legacy_value_and_persists_indicator_id(self):
        legacy = DataCheckin(
            id="legacy-checkin",
            indicator_id=self.quantitative.id,
            user_id=self.owner.id,
            actual_value={"value": 73},
            submitted_at=datetime.now(timezone.utc),
        )
        async with self.Session() as session:
            session.add(legacy)
            await session.commit()

            def fake_run_d_stage(indicators, actuals, _feedback):
                self.assertEqual(actuals[self.quantitative.id], 73)
                self.assertEqual(actuals[self.qualitative.id], 0)
                self.assertEqual(actuals[self.redline.id], 0)
                self.assertEqual(
                    {item["indicator_id"] for item in indicators},
                    {
                        self.quantitative.id,
                        self.qualitative.id,
                        self.redline.id,
                    },
                )
                return {
                    "d_result": {
                        "indicator_results": [
                            {
                                "indicator_id": self.quantitative.id,
                                "name": self.quantitative.name,
                            }
                        ],
                        "overall_progress": 73,
                        "weighted_achievement": 73,
                        "time_progress": 80,
                        "deviation": -7,
                        "overall_status": "red",
                    },
                    "feedback_text": "Keep going",
                }

            with patch("graphs.d_graph.run_d_stage", side_effect=fake_run_d_stage):
                report = await generate_diagnostic_report(
                    session, self.owner, self.goal.id
                )

            self.assertEqual(
                report.indicators_analysis["indicator_results"][0]["indicator_id"],
                self.quantitative.id,
            )

    async def test_goal_indicator_and_diagnostic_endpoints_enforce_object_scope(self):
        report = DiagnosticReport(
            id="report-1",
            goal_id=self.goal.id,
            user_id=self.owner.id,
            report_date=date(2026, 7, 15),
        )
        async with self.Session() as session:
            session.add(report)
            await session.commit()

            owner_goal = await get_goal_by_user(
                session, self.owner, self.owner.id, self.period.id
            )
            manager_indicators = await list_goal_indicators(
                session, self.manager, self.goal.id
            )
            manager_report = await get_diagnostic_report(
                session, self.manager, report.id
            )
            self.assertEqual(owner_goal.id, self.goal.id)
            self.assertEqual(len(manager_indicators), 3)
            self.assertEqual(manager_report.id, report.id)

            outsider_operations = [
                lambda: get_goal_by_user(
                    session, self.outsider, self.owner.id, self.period.id
                ),
                lambda: list_goal_indicators(session, self.outsider, self.goal.id),
                lambda: generate_diagnostic_report(
                    session, self.outsider, self.goal.id
                ),
                lambda: get_diagnostic_report(session, self.outsider, report.id),
                lambda: list_goal_reports(session, self.outsider, self.goal.id),
                lambda: get_latest_report(session, self.outsider, self.goal.id),
            ]
            for operation in outsider_operations:
                with self.assertRaises(AppException) as denied:
                    await operation()
                self.assertEqual(denied.exception.status_code, 403)

    async def test_coaching_request_is_private_to_requester_manager_and_admin(self):
        report = DiagnosticReport(
            id="report-coaching",
            goal_id=self.goal.id,
            user_id=self.owner.id,
            report_date=date(2026, 7, 15),
        )
        async with self.Session() as session:
            session.add(report)
            await session.commit()

            request = await create_coaching_request(
                session,
                self.owner,
                report.id,
                "Need help",
            )
            owner_view = await get_coaching_request(
                session, self.owner, request.id
            )
            manager_view = await get_coaching_request(
                session, self.team_lead, request.id
            )
            self.assertEqual(owner_view.id, request.id)
            self.assertEqual(manager_view.id, request.id)

            for operation in (
                lambda: create_coaching_request(
                    session, self.outsider, report.id, "Steal request"
                ),
                lambda: get_coaching_request(session, self.outsider, request.id),
                lambda: update_request_status(
                    session, self.outsider, request.id, "accepted"
                ),
            ):
                with self.assertRaises(AppException) as denied:
                    await operation()
                self.assertEqual(denied.exception.status_code, 403)

            updated = await update_request_status(
                session, self.team_lead, request.id, "accepted"
            )
            self.assertEqual(updated.status.value, "accepted")


if __name__ == "__main__":
    unittest.main()
