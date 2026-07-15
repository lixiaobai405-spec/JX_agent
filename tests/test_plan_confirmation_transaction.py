import asyncio
import copy
import os
import tempfile
import unittest
from datetime import datetime, timezone

from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.v1.plan.service import confirm_contract, update_contract_targets
from core.database import Base
from core.exceptions import AppException, GoalAlreadyExistsError
from models.action_phase import InheritanceSuggestion, SuggestionStatus, SuggestionType
from models.check_phase import Goal, Indicator
from models.period import Period, PeriodStatus
from models.plan_phase import JobAnalysis, JobPrototype, PerformanceContract
from models.user import User, UserRole

# Register every table referenced by foreign keys in the test schema.
import models.organization  # noqa: F401


class PlanConfirmationTransactionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.db_path = handle.name
        database_url = f"sqlite+aiosqlite:///{self.db_path.replace(os.sep, '/')}"
        self.engine = create_async_engine(
            database_url,
            connect_args={"timeout": 10},
        )
        self.Session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.statements: list[str] = []

        def capture_sql(_conn, _cursor, statement, _params, _context, _many):
            self.statements.append(statement.strip())

        self.capture_sql = capture_sql
        event.listen(
            self.engine.sync_engine,
            "before_cursor_execute",
            self.capture_sql,
        )

        now = datetime.now(timezone.utc)
        self.manager = User(
            id="manager-1",
            username="manager-1",
            full_name="Manager",
            email="manager-1@example.com",
            hashed_password="hashed",
            role=UserRole.manager,
        )
        self.employee = User(
            id="employee-1",
            username="employee-1",
            full_name="Employee",
            email="employee-1@example.com",
            hashed_password="hashed",
            role=UserRole.employee,
            manager_id=self.manager.id,
        )
        self.outsider = User(
            id="outsider-1",
            username="outsider-1",
            full_name="Outsider",
            email="outsider-1@example.com",
            hashed_password="hashed",
            role=UserRole.employee,
        )
        self.period = Period(
            id="period-1",
            user_id=self.employee.id,
            name="Period",
            start_date=now,
            end_date=now,
            status=PeriodStatus.draft,
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
        self.analysis = JobAnalysis(
            id="analysis-1",
            user_id=self.employee.id,
            jd_text="jd",
            job_prototype_code="P",
            analysis_result={},
        )
        self.suggestion = InheritanceSuggestion(
            id="suggestion-1",
            user_id=self.employee.id,
            previous_development_plan_id="previous-plan",
            previous_final_result_id="previous-result",
            new_period_id=self.period.id,
            suggestion_type=SuggestionType.new_indicator,
            suggestions={"summary": "Carry forward"},
            status=SuggestionStatus.accepted,
            accepted_at=now,
        )
        self.contract = PerformanceContract(
            id="contract-1",
            job_prototype_code="P",
            strategy_config={},
            contract_data={
                "period_id": self.period.id,
                "user_id": self.employee.id,
                "job_analysis_id": self.analysis.id,
                "suggested_position_name": "Senior Project Engineer",
                "assessment_period": "quarterly",
                "coaching_period": "biweekly",
                "result_application": "project bonus",
                "indicators": [
                    {
                        "id": 101,
                        "name": "Carried milestone",
                        "definition": "Complete the inherited milestone",
                        "type": "positive",
                        "unit": "percent",
                        "target": 100,
                        "target_display": "100%",
                        "target_logic": "carry forward",
                        "weight": 100,
                        "scoring_rule": "ratio",
                        "is_redline": False,
                        "source_suggestion_id": self.suggestion.id,
                    },
                    {
                        "id": 102,
                        "name": "Safety",
                        "definition": "No major safety incident",
                        "type": "redline",
                        "unit": "count",
                        "target": 0,
                        "target_display": "0",
                        "target_logic": "zero tolerance",
                        "weight": 0,
                        "scoring_rule": "binary",
                        "is_redline": True,
                        "source_suggestion_id": None,
                    },
                ],
            },
            ai_generated=True,
        )
        async with self.Session() as session:
            session.add_all(
                [
                    self.manager,
                    self.employee,
                    self.outsider,
                    self.period,
                    self.prototype,
                    self.analysis,
                    self.suggestion,
                    self.contract,
                ]
            )
            await session.commit()
        self.statements.clear()

    async def asyncTearDown(self):
        event.remove(
            self.engine.sync_engine,
            "before_cursor_execute",
            self.capture_sql,
        )
        await self.engine.dispose()
        os.unlink(self.db_path)

    async def _confirm_in_new_session(self):
        async with self.Session() as session:
            return await confirm_contract(
                session,
                self.manager,
                self.contract.id,
                self.outsider.id,
            )

    async def test_target_update_acquires_sqlite_write_lock_before_reading_contract(self):
        self.statements.clear()
        async with self.Session() as session:
            updated = await update_contract_targets(
                session,
                self.manager,
                self.contract.id,
                [{"indicator_id": 101, "target": 125.5}],
            )

        self.assertEqual(updated.contract_data["indicators"][0]["target"], 125.5)
        self.assertTrue(self.statements)
        self.assertEqual(self.statements[0].upper(), "BEGIN IMMEDIATE")

    async def test_two_sessions_create_one_goal_and_atomically_adopt_suggestion(self):
        results = await asyncio.gather(
            self._confirm_in_new_session(),
            self._confirm_in_new_session(),
            return_exceptions=True,
        )

        successes = [result for result in results if isinstance(result, PerformanceContract)]
        failures = [result for result in results if isinstance(result, Exception)]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertIsInstance(failures[0], AppException)
        self.assertGreaterEqual(
            sum(statement.upper().startswith("BEGIN IMMEDIATE") for statement in self.statements),
            2,
        )

        async with self.Session() as session:
            goal_count = await session.scalar(
                select(func.count()).select_from(Goal).where(
                    Goal.owner_user_id == self.employee.id,
                    Goal.period_id == self.period.id,
                )
            )
            outsider_goal_count = await session.scalar(
                select(func.count()).select_from(Goal).where(
                    Goal.owner_user_id == self.outsider.id,
                    Goal.period_id == self.period.id,
                )
            )
            self.assertEqual(goal_count, 1)
            self.assertEqual(outsider_goal_count, 0)

            goal = (
                await session.execute(
                    select(Goal).where(
                        Goal.owner_user_id == self.employee.id,
                        Goal.period_id == self.period.id,
                    )
                )
            ).scalar_one()
            self.assertEqual(goal.title, "Senior Project Engineer")

            indicators = (
                await session.execute(select(Indicator).where(Indicator.goal_id == goal.id))
            ).scalars().all()
            self.assertEqual(len(indicators), 2)
            carried = next(item for item in indicators if item.name == "Carried milestone")
            self.assertEqual(
                carried.definition,
                "Complete the inherited milestone；目标：100%；目标依据：carry forward；评分：ratio",
            )

            suggestion = await session.get(InheritanceSuggestion, self.suggestion.id)
            self.assertEqual(suggestion.adopted_goal_id, goal.id)
            self.assertEqual(suggestion.adopted_indicator_id, carried.id)

            contract = await session.get(PerformanceContract, self.contract.id)
            self.assertEqual(contract.goal_id, goal.id)
            self.assertEqual(contract.confirmed_by, self.manager.id)
            period = await session.get(Period, self.period.id)
            self.assertEqual(period.status, PeriodStatus.open)

    async def test_two_period_confirmations_leave_only_one_period_open(self):
        second_period = Period(
            id="period-2",
            user_id=self.employee.id,
            name="Second Period",
            start_date=self.period.start_date,
            end_date=self.period.end_date,
            status=PeriodStatus.draft,
        )
        async with self.Session() as session:
            first_contract = await session.get(PerformanceContract, self.contract.id)
            first_data = copy.deepcopy(first_contract.contract_data)
            for indicator in first_data["indicators"]:
                indicator.pop("source_suggestion_id", None)
            first_contract.contract_data = first_data

            second_data = copy.deepcopy(first_data)
            second_data["period_id"] = second_period.id
            second_contract = PerformanceContract(
                id="contract-2",
                job_prototype_code=self.prototype.code,
                strategy_config={},
                contract_data=second_data,
                ai_generated=True,
            )
            session.add_all([second_period, second_contract])
            await session.commit()

        async def confirm(contract_id: str):
            async with self.Session() as session:
                manager = await session.get(User, self.manager.id)
                return await confirm_contract(
                    session,
                    manager,
                    contract_id,
                    self.outsider.id,
                )

        results = await asyncio.gather(
            confirm(self.contract.id),
            confirm("contract-2"),
        )
        self.assertEqual(len(results), 2)

        async with self.Session() as session:
            periods = list(
                (
                    await session.execute(
                        select(Period).where(
                            Period.id.in_((self.period.id, second_period.id))
                        )
                    )
                )
                .scalars()
                .all()
            )
            contracts = list(
                (
                    await session.execute(
                        select(PerformanceContract).where(
                            PerformanceContract.id.in_(
                                (self.contract.id, "contract-2")
                            )
                        )
                    )
                )
                .scalars()
                .all()
            )
            goal_count = await session.scalar(
                select(func.count()).select_from(Goal).where(
                    Goal.period_id.in_((self.period.id, second_period.id))
                )
            )

        self.assertEqual(
            sum(period.status == PeriodStatus.open for period in periods),
            1,
        )
        self.assertTrue(all(contract.confirmed_at is not None for contract in contracts))
        self.assertEqual(goal_count, 2)

    async def test_existing_employee_goal_blocks_client_owner_spoof(self):
        existing_goal = Goal(
            id="existing-goal",
            owner_user_id=self.employee.id,
            period_id=self.period.id,
            title="Existing",
            created_by=self.manager.id,
        )
        async with self.Session() as session:
            session.add(existing_goal)
            await session.commit()

        async with self.Session() as session:
            with self.assertRaises(GoalAlreadyExistsError):
                await confirm_contract(
                    session,
                    self.manager,
                    self.contract.id,
                    self.outsider.id,
                )

        async with self.Session() as session:
            goal_count = await session.scalar(
                select(func.count()).select_from(Goal).where(Goal.period_id == self.period.id)
            )
            self.assertEqual(goal_count, 1)

    async def test_stale_suggestion_rolls_back_goal_and_confirmation(self):
        async with self.Session() as session:
            suggestion = await session.get(InheritanceSuggestion, self.suggestion.id)
            suggestion.status = SuggestionStatus.rejected
            await session.commit()

        async with self.Session() as session:
            with self.assertRaises(AppException):
                await confirm_contract(
                    session,
                    self.manager,
                    self.contract.id,
                    self.outsider.id,
                )

        async with self.Session() as session:
            goal_count = await session.scalar(select(func.count()).select_from(Goal))
            self.assertEqual(goal_count, 0)
            contract = await session.get(PerformanceContract, self.contract.id)
            self.assertIsNone(contract.confirmed_at)
            self.assertIsNone(contract.goal_id)

    async def test_closed_period_cannot_be_confirmed(self):
        async with self.Session() as session:
            period = await session.get(Period, self.period.id)
            period.status = PeriodStatus.closed
            await session.commit()

        async with self.Session() as session:
            with self.assertRaises(AppException):
                await confirm_contract(
                    session,
                    self.manager,
                    self.contract.id,
                    self.outsider.id,
                )

    async def test_tampered_indicator_contract_is_revalidated_before_goal_creation(self):
        async with self.Session() as session:
            contract = await session.get(PerformanceContract, self.contract.id)
            contract_data = dict(contract.contract_data)
            indicators = [dict(item) for item in contract_data["indicators"]]
            indicators[0]["weight"] = 50
            contract_data["indicators"] = indicators
            contract.contract_data = contract_data
            await session.commit()

        async with self.Session() as session:
            with self.assertRaises(AppException):
                await confirm_contract(
                    session,
                    self.manager,
                    self.contract.id,
                    self.outsider.id,
                )

        async with self.Session() as session:
            goal_count = await session.scalar(select(func.count()).select_from(Goal))
            self.assertEqual(goal_count, 0)

    async def test_legacy_contract_without_indicator_ids_can_still_be_confirmed(self):
        async with self.Session() as session:
            contract = await session.get(PerformanceContract, self.contract.id)
            legacy_indicators = []
            for item in contract.contract_data["indicators"]:
                legacy_item = dict(item)
                legacy_item.pop("id", None)
                legacy_item.pop("source_suggestion_id", None)
                legacy_indicators.append(legacy_item)
            contract.contract_data = {
                "period_id": self.period.id,
                "indicators": legacy_indicators,
            }
            await session.commit()

        async with self.Session() as session:
            confirmed = await confirm_contract(
                session,
                self.manager,
                self.contract.id,
                self.outsider.id,
            )
            self.assertIsNotNone(confirmed.goal_id)

        async with self.Session() as session:
            goal = (
                await session.execute(
                    select(Goal).where(Goal.period_id == self.period.id)
                )
            ).scalar_one()
            self.assertEqual(goal.owner_user_id, self.employee.id)


if __name__ == "__main__":
    unittest.main()
