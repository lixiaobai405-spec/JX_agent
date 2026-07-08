import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from api.v1.do import service as do_service
from models.check_phase import Goal, Indicator
from models.do_phase import TrafficLightStatus
from models.period import Period
from models.user import User
from scripts.verify_p_stage_contract import verify_p_stage_contract


S_ROLE_ACTUALS = {
    "区域净销售额": 520,
    "新品铺货率": 70,
    "销售回款率": 96,
    "巡店SOP执行": 90,
    "乱价/串货行为": 0,
}


def _assert_mock_mode() -> None:
    assert os.getenv("USE_MOCK", "").lower() == "true", "Run with USE_MOCK=true"


async def _scalar_one(session, model, *conditions):
    result = await session.execute(select(model).where(*conditions))
    return result.scalar_one()


class _session_context:
    async def __aenter__(self):
        from core.database import AsyncSessionLocal

        self.session = AsyncSessionLocal()
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()


async def _verify_d_stage_demo_impl() -> None:
    async with _session_context() as session:
        user = await _scalar_one(session, User, User.username == "demo_sales")
        manager = await _scalar_one(session, User, User.username == "demo_manager")
        period = await _scalar_one(
            session,
            Period,
            Period.user_id == user.id,
            Period.name == "2026年7月绩效演示周期",
            Period.deleted_at.is_(None),
        )
        goal = await _scalar_one(
            session,
            Goal,
            Goal.owner_user_id == user.id,
            Goal.period_id == period.id,
            Goal.deleted_at.is_(None),
        )

        indicators_result = await session.execute(
            select(Indicator).where(
                Indicator.goal_id == goal.id,
                Indicator.deleted_at.is_(None),
            )
        )
        indicators = {indicator.name: indicator for indicator in indicators_result.scalars().all()}
        assert set(S_ROLE_ACTUALS).issubset(indicators), sorted(indicators)

        for name, actual in S_ROLE_ACTUALS.items():
            await do_service.submit_checkin(
                session,
                current_user=user,
                indicator_id=indicators[name].id,
                actual_value=actual,
                progress_description=f"{name}演示打卡：实际值{actual}",
                issues="核心便利系统推进偏慢" if name in {"区域净销售额", "新品铺货率"} else None,
            )

        report = await do_service.generate_diagnostic_report(
            session,
            current_user=user,
            goal_id=goal.id,
            feedback="本月便利系统竞争促销加剧，部分门店谈判周期延长。",
        )

        status = report.traffic_light_status.value if isinstance(report.traffic_light_status, TrafficLightStatus) else report.traffic_light_status
        assert status in {"yellow", "red"}, f"Unexpected traffic light {status}"
        assert report.weighted_achievement_rate is not None, "Missing weighted_achievement_rate"
        assert report.time_progress is not None, "Missing time_progress"
        assert report.progress_deviation is not None, "Missing progress_deviation"
        assert report.overall_progress is not None, "Missing overall_progress"
        assert report.indicators_analysis, "Missing indicators_analysis"
        assert report.root_cause_analysis, "Missing root_cause_analysis"
        assert report.improvement_suggestions, "Missing improvement_suggestions"

        request = await do_service.create_coaching_request(
            session,
            current_user=user,
            diagnostic_report_id=report.id,
            request_reason="希望上级协助复盘重点便利系统客户转化问题",
            urgency_level="normal",
        )
        assert request.manager_id == manager.id, "Coaching request manager mismatch"

    print("D_STAGE_DEMO_OK")


async def verify_d_stage_demo() -> None:
    _assert_mock_mode()
    await verify_p_stage_contract()
    await _verify_d_stage_demo_impl()


if __name__ == "__main__":
    asyncio.run(verify_d_stage_demo())
