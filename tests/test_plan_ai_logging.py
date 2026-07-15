import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.v1.plan.service import create_job_analysis, generate_contract
from core.database import Base
from core.exceptions import ContractGenerationFailedError, JobAnalysisFailedError
from graphs.p_graph import ClassifyResult, Indicator as GraphIndicator, PStageResult
from models.period import Period, PeriodStatus
from models.plan_phase import (
    AIGenerationLog,
    JobAnalysis,
    JobPrototype,
    PerformanceContract,
)
from models.user import User, UserRole

# Register all foreign-key targets used by the test schema.
import models.action_phase  # noqa: F401
import models.check_phase  # noqa: F401
import models.organization  # noqa: F401


class PlanAILoggingTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.Session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.employee = User(
            id="employee-1",
            username="employee-1",
            full_name="Employee",
            email="employee-1@example.com",
            hashed_password="hashed",
            role=UserRole.employee,
        )
        self.period = Period(
            id="period-1",
            user_id=self.employee.id,
            name="Period",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc),
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
        async with self.Session() as session:
            session.add_all([self.employee, self.period, self.prototype])
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    @staticmethod
    def _classification() -> ClassifyResult:
        return ClassifyResult(
            score_quantifiability=5,
            score_output_cycle=8,
            score_work_nature=4,
            position_type="P",
            position_type_name="Project",
            classification_reasoning="Milestone driven",
        )

    @classmethod
    def _p_result(cls) -> PStageResult:
        return PStageResult(
            position_type="P",
            position_type_name="Project",
            suggested_position_name="Senior Project Engineer",
            classification_reasoning="Milestone driven",
            assessment_period="quarterly",
            coaching_period="biweekly",
            result_application="project bonus",
            indicators=[
                GraphIndicator(
                    id=101,
                    name="Milestone completion",
                    definition="Complete committed milestones",
                    type="positive",
                    unit="percent",
                    target=100,
                    target_display="100%",
                    target_logic="project plan",
                    weight=100,
                    scoring_rule="actual / target",
                    is_redline=False,
                ),
                GraphIndicator(
                    id=102,
                    name="Safety incident",
                    definition="No major safety incident",
                    type="redline",
                    unit="count",
                    target=0,
                    target_display="0",
                    target_logic="zero tolerance",
                    weight=0,
                    scoring_rule="binary",
                    is_redline=True,
                ),
            ],
        )

    async def test_failed_analysis_writes_durable_log_in_independent_session(self):
        async with self.Session() as session:
            with patch(
                "graphs.p_graph.run_classify_only",
                new=AsyncMock(side_effect=TimeoutError("classification timed out")),
            ):
                with self.assertRaises(JobAnalysisFailedError) as raised:
                    await create_job_analysis(
                        session,
                        self.employee,
                        self.employee.id,
                        "jd",
                    )

            self.assertGreaterEqual(raised.exception.status_code, 400)
            await session.rollback()

        async with self.Session() as verification_session:
            result = await verification_session.execute(
                select(AIGenerationLog).where(AIGenerationLog.job_type == "analysis")
            )
            log = result.scalar_one()
            self.assertFalse(log.success)
            self.assertEqual(log.user_id, self.employee.id)
            self.assertIn("classification timed out", log.error_message)

    async def test_successful_analysis_log_references_created_analysis(self):
        async with self.Session() as session:
            with patch(
                "graphs.p_graph.run_classify_only",
                new=AsyncMock(return_value=self._classification()),
            ):
                analysis = await create_job_analysis(
                    session,
                    self.employee,
                    self.employee.id,
                    "jd",
                )

        async with self.Session() as verification_session:
            result = await verification_session.execute(
                select(AIGenerationLog).where(AIGenerationLog.job_type == "analysis")
            )
            log = result.scalar_one()
            self.assertTrue(log.success)
            self.assertEqual(log.job_analysis_id, analysis.id)

    async def test_contract_generation_logs_success_and_preserves_metadata(self):
        analysis = JobAnalysis(
            id="analysis-1",
            user_id=self.employee.id,
            jd_text="jd",
            job_prototype_code="P",
            analysis_result={"classify_result": self._classification().model_dump()},
        )
        async with self.Session() as session:
            session.add(analysis)
            await session.commit()

            with patch(
                "graphs.p_graph.run_generate_indicators",
                new=AsyncMock(return_value=self._p_result()),
            ):
                contract = await generate_contract(
                    session,
                    self.employee,
                    self.period.id,
                    self.employee.id,
                    analysis.id,
                )

            self.assertEqual(
                contract.contract_data["suggested_position_name"],
                "Senior Project Engineer",
            )
            self.assertEqual(contract.contract_data["assessment_period"], "quarterly")
            self.assertEqual(contract.contract_data["coaching_period"], "biweekly")
            self.assertEqual(contract.contract_data["result_application"], "project bonus")
            self.assertEqual(
                contract.contract_data["indicators"][0]["definition"],
                "Complete committed milestones",
            )

        async with self.Session() as verification_session:
            result = await verification_session.execute(
                select(AIGenerationLog).where(AIGenerationLog.job_type == "contract")
            )
            log = result.scalar_one()
            self.assertTrue(log.success)
            self.assertEqual(log.job_analysis_id, analysis.id)

    async def test_failed_contract_generation_writes_durable_log(self):
        analysis = JobAnalysis(
            id="analysis-1",
            user_id=self.employee.id,
            jd_text="jd",
            job_prototype_code="P",
            analysis_result={"classify_result": self._classification().model_dump()},
        )
        async with self.Session() as session:
            session.add(analysis)
            await session.commit()

            with patch(
                "graphs.p_graph.run_generate_indicators",
                new=AsyncMock(side_effect=TimeoutError("indicator generation timed out")),
            ):
                with self.assertRaises(ContractGenerationFailedError) as raised:
                    await generate_contract(
                        session,
                        self.employee,
                        self.period.id,
                        self.employee.id,
                        analysis.id,
                    )

            self.assertGreaterEqual(raised.exception.status_code, 400)
            await session.rollback()

        async with self.Session() as verification_session:
            result = await verification_session.execute(
                select(AIGenerationLog).where(AIGenerationLog.job_type == "contract")
            )
            log = result.scalar_one()
            self.assertFalse(log.success)
            self.assertEqual(log.job_analysis_id, "analysis-1")
            self.assertIn("indicator generation timed out", log.error_message)

    async def test_contract_generation_rejects_duplicate_stable_indicator_ids(self):
        analysis = JobAnalysis(
            id="analysis-1",
            user_id=self.employee.id,
            jd_text="jd",
            job_prototype_code="P",
            analysis_result={"classify_result": self._classification().model_dump()},
        )
        duplicate_result = self._p_result()
        duplicate_result.indicators[1].id = duplicate_result.indicators[0].id

        async with self.Session() as session:
            session.add(analysis)
            await session.commit()
            with patch(
                "graphs.p_graph.run_generate_indicators",
                new=AsyncMock(return_value=duplicate_result),
            ):
                with self.assertRaises(ContractGenerationFailedError):
                    await generate_contract(
                        session,
                        self.employee,
                        self.period.id,
                        self.employee.id,
                        analysis.id,
                    )

        async with self.Session() as session:
            count = await session.scalar(
                select(func.count()).select_from(PerformanceContract)
            )
            self.assertEqual(count, 0)

    async def test_malformed_analysis_is_logged_as_contract_generation_failure(self):
        analysis = JobAnalysis(
            id="analysis-1",
            user_id=self.employee.id,
            jd_text="jd",
            job_prototype_code="P",
            analysis_result=None,
        )
        async with self.Session() as session:
            session.add(analysis)
            await session.commit()
            with self.assertRaises(ContractGenerationFailedError):
                await generate_contract(
                    session,
                    self.employee,
                    self.period.id,
                    self.employee.id,
                    analysis.id,
                )

        async with self.Session() as session:
            result = await session.execute(
                select(AIGenerationLog).where(
                    AIGenerationLog.job_type == "contract",
                    AIGenerationLog.success.is_(False),
                )
            )
            self.assertIsNotNone(result.scalar_one_or_none())


if __name__ == "__main__":
    unittest.main()
