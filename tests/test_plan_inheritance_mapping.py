import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.v1.action.service import generate_inheritance_suggestions
from api.v1.plan.service import generate_contract
from core.database import Base
from core.exceptions import (
    ContractGenerationFailedError,
    InheritanceSuggestionNotFoundError,
)
from graphs.p_graph import (
    ClassifyResult,
    Indicator as GraphIndicator,
    PStageResult,
    _generate_indicators_llm,
)
from models.action_phase import InheritanceSuggestion, SuggestionStatus, SuggestionType
from models.period import Period, PeriodStatus
from models.plan_phase import JobAnalysis, JobPrototype, PerformanceContract
from models.user import User, UserRole

# Register all foreign-key targets used by the test schema.
import models.check_phase  # noqa: F401
import models.organization  # noqa: F401


def test_graph_indicator_serializes_optional_source_suggestion_id():
    indicator = GraphIndicator(
        id=1,
        name="Inherited metric",
        definition="Definition",
        type="positive",
        unit="percent",
        target=100,
        target_display="100%",
        target_logic="carry forward",
        weight=100,
        scoring_rule="ratio",
        is_redline=False,
        source_suggestion_id="suggestion-1",
    )
    assert indicator.model_dump()["source_suggestion_id"] == "suggestion-1"


def test_indicator_prompt_includes_stable_inheritance_id():
    classification = ClassifyResult(
        score_quantifiability=5,
        score_output_cycle=8,
        score_work_nature=4,
        position_type="P",
        position_type_name="Project",
        classification_reasoning="Milestone driven",
    )
    strategy = {
        "assessment_period": "quarterly",
        "indicator_count": "3",
        "quantitative_ratio": "100%",
        "coaching": "biweekly",
        "result_application": "bonus",
    }
    prompt = _generate_indicators_llm.__wrapped__(
        "jd",
        "P",
        classification,
        strategy,
        None,
        [{"id": "suggestion-1", "suggestions": {"summary": "Carry forward"}}],
    )
    assert "suggestion-1" in prompt
    assert "source_suggestion_id" in prompt


class PlanInheritanceGenerationTest(unittest.IsolatedAsyncioTestCase):
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
            start_date=now,
            end_date=now,
            status=PeriodStatus.draft,
        )
        self.prototype = JobPrototype(
            id="prototype-p",
            code="P",
            name="Project",
            indicator_count_min=3,
            indicator_count_max=3,
            quantitative_ratio_min=1,
            quantitative_ratio_max=1,
            primary_target_setting="mixed",
        )
        self.classification = ClassifyResult(
            score_quantifiability=5,
            score_output_cycle=8,
            score_work_nature=4,
            position_type="P",
            position_type_name="Project",
            classification_reasoning="Milestone driven",
        )
        self.analysis = JobAnalysis(
            id="analysis-1",
            user_id=self.employee.id,
            jd_text="jd",
            job_prototype_code="P",
            analysis_result={"classify_result": self.classification.model_dump()},
        )
        self.accepted = [
            self._suggestion("suggestion-1", SuggestionStatus.accepted),
            self._suggestion("suggestion-2", SuggestionStatus.accepted),
        ]
        self.pending = self._suggestion("suggestion-pending", SuggestionStatus.pending)
        self.adopted = self._suggestion("suggestion-adopted", SuggestionStatus.accepted)
        self.adopted.adopted_goal_id = "existing-goal"
        self.adopted.adopted_indicator_id = "existing-indicator"

        async with self.Session() as session:
            session.add_all(
                [
                    self.employee,
                    self.period,
                    self.prototype,
                    self.analysis,
                    *self.accepted,
                    self.pending,
                    self.adopted,
                ]
            )
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    def _suggestion(
        self,
        suggestion_id: str,
        status: SuggestionStatus,
    ) -> InheritanceSuggestion:
        return InheritanceSuggestion(
            id=suggestion_id,
            user_id=self.employee.id,
            previous_development_plan_id=f"plan-{suggestion_id}",
            previous_final_result_id=f"result-{suggestion_id}",
            new_period_id=self.period.id,
            suggestion_type=SuggestionType.new_indicator,
            suggestions={"summary": suggestion_id},
            status=status,
        )

    @staticmethod
    def _p_result(source_ids: list[str]) -> PStageResult:
        indicators = []
        for index in range(1, 3):
            source_id = source_ids[index - 1] if index <= len(source_ids) else None
            indicators.append(
                GraphIndicator(
                    id=index,
                    name=f"Inherited {index}",
                    definition=f"Definition {index}",
                    type="positive",
                    unit="percent",
                    target=100,
                    target_display="100%",
                    target_logic="carry forward",
                    weight=50,
                    scoring_rule="ratio",
                    is_redline=False,
                    source_suggestion_id=source_id,
                )
            )
        indicators.append(
            GraphIndicator(
                id=99,
                name="Safety",
                definition="No incident",
                type="redline",
                unit="count",
                target=0,
                target_display="0",
                target_logic="zero tolerance",
                weight=0,
                scoring_rule="binary",
                is_redline=True,
            )
        )
        return PStageResult(
            position_type="P",
            position_type_name="Project",
            suggested_position_name="Project Engineer",
            classification_reasoning="Milestone driven",
            assessment_period="quarterly",
            indicators=indicators,
            coaching_period="biweekly",
            result_application="bonus",
        )

    async def test_generation_fails_when_any_injected_suggestion_id_is_missing(self):
        async with self.Session() as session:
            with patch(
                "graphs.p_graph.run_generate_indicators",
                new=AsyncMock(return_value=self._p_result(["suggestion-1"])),
            ):
                with self.assertRaises(ContractGenerationFailedError):
                    await generate_contract(
                        session,
                        self.employee,
                        self.period.id,
                        self.employee.id,
                        self.analysis.id,
                    )

        async with self.Session() as session:
            contract_count = await session.scalar(
                select(func.count()).select_from(PerformanceContract)
            )
            self.assertEqual(contract_count, 0)

    async def test_generation_injects_only_accepted_unadopted_and_preserves_mapping(self):
        mocked_generation = AsyncMock(
            return_value=self._p_result(["suggestion-1", "suggestion-2"])
        )
        async with self.Session() as session:
            with patch(
                "graphs.p_graph.run_generate_indicators",
                new=mocked_generation,
            ):
                contract = await generate_contract(
                    session,
                    self.employee,
                    self.period.id,
                    self.employee.id,
                    self.analysis.id,
                )

        inherited_payload = mocked_generation.await_args.kwargs["inherited_suggestions"]
        self.assertEqual(
            {item["id"] for item in inherited_payload},
            {"suggestion-1", "suggestion-2"},
        )
        self.assertEqual(
            {
                item["source_suggestion_id"]
                for item in contract.contract_data["indicators"]
                if item.get("source_suggestion_id")
            },
            {"suggestion-1", "suggestion-2"},
        )

    async def test_no_action_source_data_returns_404(self):
        async with self.Session() as session:
            with self.assertRaises(InheritanceSuggestionNotFoundError) as raised:
                await generate_inheritance_suggestions(
                    session,
                    self.employee,
                    self.employee.id,
                    "missing-source-period",
                    self.period.id,
                )

        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
