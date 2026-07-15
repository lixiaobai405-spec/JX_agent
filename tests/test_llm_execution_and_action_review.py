import threading
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.v1.action.service import ai_review_plan
from core.database import Base
from core.exceptions import AppException
from graphs.p_graph import ClassifyResult, run_classify_only
from models.action_phase import DevelopmentPlan, ReviewReport
from models.check_phase import FinalResult, FinalResultStatus, Goal
from models.period import Period, PeriodStatus
from models.user import User, UserRole
from utils.llm import retry_and_validate, run_sync_llm

# Register tables referenced by foreign keys in this test database.
import models.organization  # noqa: F401
import models.plan_phase  # noqa: F401
from models.plan_phase import AIGenerationLog


class LLMExecutionTest(unittest.IsolatedAsyncioTestCase):
    async def test_default_execution_does_not_multiply_validation_retries(self):
        class Result(BaseModel):
            value: int

        class InvalidClient:
            def __init__(self):
                self.calls = 0

            def call_stream(self, *_args, **_kwargs):
                self.calls += 1
                return '{"wrong": true}'

        client = InvalidClient()

        @retry_and_validate(response_model=Result, max_attempts=3)
        def generate():
            return "Return a value"

        with patch("utils.llm.get_llm_client", return_value=client):
            with self.assertRaises(Exception):
                await run_sync_llm(generate, timeout_seconds=1)

        self.assertEqual(client.calls, 3)

    async def test_validation_layer_retries_transport_failure(self):
        class Result(BaseModel):
            value: int

        class FlakyClient:
            def __init__(self):
                self.calls = 0

            def call_stream(self, *_args, **_kwargs):
                self.calls += 1
                if self.calls == 1:
                    raise ConnectionError("temporary")
                return '{"value": 7}'

        client = FlakyClient()

        @retry_and_validate(response_model=Result, max_attempts=2)
        def generate():
            return "Return a value"

        with patch("utils.llm.get_llm_client", return_value=client):
            result = await run_sync_llm(generate, timeout_seconds=1)

        self.assertEqual(result.value, 7)
        self.assertEqual(client.calls, 2)

    async def test_sync_llm_runs_in_worker_thread_with_bounded_retry(self):
        event_loop_thread = threading.get_ident()
        call_threads: list[int] = []

        def flaky_call():
            call_threads.append(threading.get_ident())
            if len(call_threads) == 1:
                raise RuntimeError("transient")
            return "ok"

        result = await run_sync_llm(
            flaky_call,
            timeout_seconds=1,
            max_attempts=2,
        )

        self.assertEqual(result, "ok")
        self.assertEqual(len(call_threads), 2)
        self.assertTrue(all(thread_id != event_loop_thread for thread_id in call_threads))

    async def test_sync_llm_timeout_is_explicit_and_does_not_retry_forever(self):
        release = threading.Event()
        calls = 0

        def blocked_call():
            nonlocal calls
            calls += 1
            release.wait(timeout=1)

        try:
            with self.assertRaises(TimeoutError):
                await run_sync_llm(
                    blocked_call,
                    timeout_seconds=0.01,
                    max_attempts=2,
                )
        finally:
            release.set()

        self.assertEqual(calls, 2)

    async def test_plan_classification_uses_worker_thread(self):
        event_loop_thread = threading.get_ident()
        call_thread = None
        expected = ClassifyResult(
            score_quantifiability=8,
            score_output_cycle=6,
            score_work_nature=7,
            position_type="P",
            position_type_name="project",
            classification_reasoning="test",
        )

        def fake_classify(_jd_text):
            nonlocal call_thread
            call_thread = threading.get_ident()
            return expected

        with patch("graphs.p_graph._classify_llm", side_effect=fake_classify):
            actual = await run_classify_only("jd")

        self.assertEqual(actual, expected)
        self.assertNotEqual(call_thread, event_loop_thread)


class ActionAIReviewFailureTest(unittest.IsolatedAsyncioTestCase):
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

    async def test_failed_ai_review_returns_error_and_keeps_draft_unchanged(self):
        now = datetime.now(timezone.utc)
        employee = User(
            id="employee-1",
            username="employee-1",
            full_name="Employee",
            email="employee-1@example.com",
            hashed_password="hashed",
            role=UserRole.employee,
        )
        period = Period(
            id="period-1",
            user_id=employee.id,
            name="Period",
            start_date=now,
            end_date=now,
            status=PeriodStatus.closed,
        )
        goal = Goal(
            id="goal-1",
            owner_user_id=employee.id,
            period_id=period.id,
            title="Goal",
            created_by=employee.id,
        )
        final_result = FinalResult(
            id="final-result-1",
            goal_id=goal.id,
            final_grade="B",
            confirmed_by=employee.id,
            confirmed_at=now,
            status=FinalResultStatus.confirmed,
        )
        report = ReviewReport(
            id="report-1",
            final_result_id=final_result.id,
            user_id=employee.id,
            report_type="b",
            strengths_analysis={},
            improvement_areas={"areas": []},
            ai_generated=True,
            generated_at=now,
        )
        plan = DevelopmentPlan(
            id="plan-1",
            review_report_id=report.id,
            user_id=employee.id,
            goals={"text": "Original goal"},
            actions={"text": "Original action"},
            status="draft",
            ai_reviewed=False,
        )

        async with self.Session() as session:
            session.add_all([employee, period, goal, final_result, report, plan])
            await session.commit()
            employee_id = employee.id
            plan_id = plan.id

            with patch(
                "api.v1.action.service.review_plan",
                new=AsyncMock(side_effect=TimeoutError("AI timed out")),
            ):
                with self.assertRaises(AppException) as raised:
                    await ai_review_plan(session, employee, plan_id)

            self.assertGreaterEqual(raised.exception.status_code, 400)
            await session.rollback()
            persisted = await session.get(DevelopmentPlan, plan_id)
            status = persisted.status.value if hasattr(persisted.status, "value") else persisted.status
            self.assertEqual(status, "draft")
            self.assertFalse(persisted.ai_reviewed)
            self.assertIsNone(persisted.smart_evaluation)
            self.assertIsNone(persisted.ai_suggestions)
            self.assertEqual(persisted.goals, {"text": "Original goal"})
            self.assertEqual(persisted.actions, {"text": "Original action"})

            log_result = await session.execute(
                select(AIGenerationLog).where(
                    AIGenerationLog.job_type == "action_review",
                    AIGenerationLog.user_id == employee_id,
                )
            )
            failure_log = log_result.scalar_one()
            self.assertFalse(failure_log.success)
            self.assertEqual(failure_log.model_used, "deepseek-chat")
            self.assertIn("AI timed out", failure_log.error_message)


if __name__ == "__main__":
    unittest.main()
