import copy
import math
import unittest
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.v1.plan.schemas import ContractTargetsUpdateRequest
from api.v1.plan.service import (
    get_contract,
    get_job_analysis,
    list_job_analyses,
    update_contract_targets,
)
from core.database import Base
from core.exceptions import AppException, PermissionDeniedError
from models.period import Period, PeriodStatus
from models.plan_phase import JobAnalysis, JobPrototype, PerformanceContract
from models.user import User, UserRole

# Register all foreign-key targets used by the test schema.
import models.action_phase  # noqa: F401
import models.check_phase  # noqa: F401
import models.organization  # noqa: F401


def test_targets_contract_forbids_extra_fields_duplicates_and_non_finite_values():
    payload = ContractTargetsUpdateRequest.model_validate(
        {"targets": [{"indicator_id": 101, "target": 125.5}]}
    )
    assert payload.targets[0].indicator_id == 101
    assert payload.targets[0].target == 125.5

    invalid_payloads = [
        {"targets": [{"indicator_id": 101, "target": math.inf}]},
        {"targets": [{"indicator_id": 101, "target": math.nan}]},
        {"targets": [{"indicator_id": 101, "target": 1, "name": "tamper"}]},
        {"targets": [{"indicator_id": 101, "target": 1}], "contract_data": {}},
        {
            "targets": [
                {"indicator_id": 101, "target": 1},
                {"indicator_id": "101", "target": 2},
            ]
        },
        {"targets": []},
    ]
    for invalid in invalid_payloads:
        with pytest.raises(ValidationError):
            ContractTargetsUpdateRequest.model_validate(invalid)


class PlanPermissionsAndTargetsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.Session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.manager = self._user("manager", UserRole.manager)
        self.team_lead = self._user(
            "team-lead",
            UserRole.manager,
            manager_id=self.manager.id,
        )
        self.employee = self._user(
            "employee",
            UserRole.employee,
            manager_id=self.team_lead.id,
        )
        self.outsider = self._user("outsider", UserRole.employee)
        self.admin = self._user("admin", UserRole.system_admin)
        self.employee_period = self._period("period-employee", self.employee.id)
        self.outsider_period = self._period("period-outsider", self.outsider.id)
        self.closed_period = self._period(
            "period-closed",
            self.employee.id,
            status=PeriodStatus.closed,
        )
        self.prototype = JobPrototype(
            id="prototype-p",
            code="P",
            name="Project",
            indicator_count_min=2,
            indicator_count_max=3,
            quantitative_ratio_min=1,
            quantitative_ratio_max=1,
            primary_target_setting="mixed",
        )
        self.employee_analysis = self._analysis("analysis-employee", self.employee.id)
        self.outsider_analysis = self._analysis("analysis-outsider", self.outsider.id)
        self.employee_contract = self._contract(
            "contract-employee",
            self.employee_period.id,
            self.employee.id,
            self.employee_analysis.id,
        )
        self.outsider_contract = self._contract(
            "contract-outsider",
            self.outsider_period.id,
            self.outsider.id,
            self.outsider_analysis.id,
        )
        self.closed_contract = self._contract(
            "contract-closed",
            self.closed_period.id,
            self.employee.id,
            self.employee_analysis.id,
        )

        async with self.Session() as session:
            session.add_all(
                [
                    self.manager,
                    self.team_lead,
                    self.employee,
                    self.outsider,
                    self.admin,
                    self.employee_period,
                    self.outsider_period,
                    self.closed_period,
                    self.prototype,
                    self.employee_analysis,
                    self.outsider_analysis,
                    self.employee_contract,
                    self.outsider_contract,
                    self.closed_contract,
                ]
            )
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    @staticmethod
    def _user(
        user_id: str,
        role: UserRole,
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
        status: PeriodStatus = PeriodStatus.draft,
    ) -> Period:
        now = datetime.now(timezone.utc)
        return Period(
            id=period_id,
            user_id=user_id,
            name=period_id,
            start_date=now,
            end_date=now,
            status=status,
        )

    @staticmethod
    def _analysis(analysis_id: str, user_id: str) -> JobAnalysis:
        return JobAnalysis(
            id=analysis_id,
            user_id=user_id,
            jd_text="jd",
            job_prototype_code="P",
            analysis_result={
                "classify_result": {
                    "score_quantifiability": 5,
                    "score_output_cycle": 8,
                    "score_work_nature": 4,
                    "position_type": "P",
                    "position_type_name": "Project",
                    "classification_reasoning": "Milestone driven",
                    "confidence": 0.9,
                }
            },
        )

    @staticmethod
    def _contract(
        contract_id: str,
        period_id: str,
        user_id: str,
        analysis_id: str,
    ) -> PerformanceContract:
        return PerformanceContract(
            id=contract_id,
            job_prototype_code="P",
            strategy_config={"keep": "unchanged"},
            contract_data={
                "period_id": period_id,
                "user_id": user_id,
                "job_analysis_id": analysis_id,
                "suggested_position_name": "Project Engineer",
                "assessment_period": "quarterly",
                "coaching_period": "biweekly",
                "result_application": "bonus",
                "indicators": [
                    {
                        "id": 101,
                        "name": "Delivery",
                        "definition": "Deliver milestones",
                        "type": "positive",
                        "unit": "percent",
                        "target": 100,
                        "target_display": "100%",
                        "target_logic": "plan",
                        "weight": 100,
                        "scoring_rule": "ratio",
                        "is_redline": False,
                    },
                    {
                        "id": 102,
                        "name": "Safety",
                        "definition": "No incident",
                        "type": "redline",
                        "unit": "count",
                        "target": 0,
                        "target_display": "0",
                        "target_logic": "zero tolerance",
                        "weight": 0,
                        "scoring_rule": "binary",
                        "is_redline": True,
                    },
                ],
            },
            ai_generated=True,
        )

    async def test_recursive_manager_and_admin_can_read_but_outsider_cannot(self):
        async with self.Session() as session:
            analysis = await get_job_analysis(
                session,
                self.manager,
                self.employee_analysis.id,
            )
            contract = await get_contract(
                session,
                self.manager,
                self.employee_contract.id,
            )
            admin_contract = await get_contract(
                session,
                self.admin,
                self.employee_contract.id,
            )
            self.assertEqual(analysis.id, self.employee_analysis.id)
            self.assertEqual(contract.id, self.employee_contract.id)
            self.assertEqual(admin_contract.id, self.employee_contract.id)

            with self.assertRaises(PermissionDeniedError):
                await get_job_analysis(
                    session,
                    self.outsider,
                    self.employee_analysis.id,
                )
            with self.assertRaises(PermissionDeniedError):
                await get_contract(
                    session,
                    self.outsider,
                    self.employee_contract.id,
                )

    async def test_manager_list_is_limited_to_recursive_team(self):
        async with self.Session() as session:
            analyses = await list_job_analyses(session, self.manager)
            self.assertEqual(
                {analysis.id for analysis in analyses},
                {self.employee_analysis.id},
            )

            with self.assertRaises(PermissionDeniedError):
                await list_job_analyses(session, self.manager, self.outsider.id)

    async def test_target_patch_changes_only_requested_non_redline_target(self):
        before = copy.deepcopy(self.employee_contract.contract_data)
        payload = ContractTargetsUpdateRequest.model_validate(
            {"targets": [{"indicator_id": 101, "target": 125.5}]}
        )

        async with self.Session() as session:
            updated = await update_contract_targets(
                session,
                self.manager,
                self.employee_contract.id,
                [target.model_dump() for target in payload.targets],
            )

        expected = copy.deepcopy(before)
        expected["indicators"][0]["target"] = 125.5
        expected["indicators"][0]["target_display"] = "125.5%"
        self.assertEqual(updated.contract_data, expected)
        self.assertEqual(updated.strategy_config, {"keep": "unchanged"})

    async def test_target_display_is_derived_from_structured_unit_not_free_text(self):
        async with self.Session() as session:
            contract = await session.get(
                PerformanceContract,
                self.employee_contract.id,
            )
            contract_data = copy.deepcopy(contract.contract_data)
            contract_data["indicators"][0]["unit"] = ""
            contract_data["indicators"][0]["target_display"] = "10月15日完成率100%"
            contract.contract_data = contract_data
            await session.commit()

            updated = await update_contract_targets(
                session,
                self.manager,
                contract.id,
                [{"indicator_id": 101, "target": 90}],
            )

        self.assertEqual(
            updated.contract_data["indicators"][0]["target_display"],
            "90",
        )

    async def test_target_patch_rejects_redline_unknown_closed_and_foreign_contracts(self):
        cases = [
            (self.employee_contract.id, self.manager, 102),
            (self.employee_contract.id, self.manager, 999),
            (self.closed_contract.id, self.manager, 101),
            (self.outsider_contract.id, self.employee, 101),
        ]
        async with self.Session() as session:
            for contract_id, actor, indicator_id in cases:
                with self.assertRaises(AppException):
                    await update_contract_targets(
                        session,
                        actor,
                        contract_id,
                        [{"indicator_id": indicator_id, "target": 10}],
                    )
                await session.rollback()

            contract = await session.get(PerformanceContract, self.employee_contract.id)
            contract.confirmed_at = datetime.now(timezone.utc)
            await session.commit()
            with self.assertRaises(AppException):
                await update_contract_targets(
                    session,
                    self.manager,
                    contract.id,
                    [{"indicator_id": 101, "target": 10}],
                )

    async def test_recursive_manager_scope_terminates_when_hierarchy_has_a_cycle(self):
        async with self.Session() as session:
            manager = await session.get(User, self.manager.id)
            manager.manager_id = self.employee.id
            await session.commit()

            connection = await session.connection()
            raw_connection = await connection.get_raw_connection()
            driver_connection = raw_connection.driver_connection
            calls = 0

            def stop_runaway_recursion() -> int:
                nonlocal calls
                calls += 1
                return int(calls > 10_000)

            await driver_connection.set_progress_handler(stop_runaway_recursion, 100)
            try:
                contract = await get_contract(
                    session,
                    self.manager,
                    self.employee_contract.id,
                )
            finally:
                await driver_connection.set_progress_handler(None, 0)

        self.assertEqual(contract.id, self.employee_contract.id)


if __name__ == "__main__":
    unittest.main()
