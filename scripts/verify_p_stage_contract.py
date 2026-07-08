import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from api.v1.plan import service as plan_service
from core.database import AsyncSessionLocal
from models.check_phase import Goal, Indicator, IndicatorDirection, ScoreMethod
from models.period import Period, PeriodStatus
from models.plan_phase import PerformanceContract
from models.user import User
from scripts.seed_demo_data import JD_CASES, seed_demo_data


EXPECTED_INDICATORS = {
    "区域净销售额": {"weight": 0.45, "direction": IndicatorDirection.positive, "redline": False},
    "新品铺货率": {"weight": 0.20, "direction": IndicatorDirection.positive, "redline": False},
    "销售回款率": {"weight": 0.20, "direction": IndicatorDirection.positive, "redline": False},
    "巡店SOP执行": {"weight": 0.15, "direction": IndicatorDirection.positive, "redline": False},
    "乱价/串货行为": {"weight": 0.0, "direction": IndicatorDirection.negative, "redline": True},
}


def _assert_mock_mode() -> None:
    assert os.getenv("USE_MOCK", "").lower() == "true", "Run with USE_MOCK=true"


async def _scalar_one(session, model, *conditions):
    result = await session.execute(select(model).where(*conditions))
    return result.scalar_one()


async def _get_existing_goal(session, user_id: str, period_id: str) -> Goal | None:
    result = await session.execute(
        select(Goal).where(
            Goal.owner_user_id == user_id,
            Goal.period_id == period_id,
            Goal.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def _repair_existing_demo_goal(session, goal: Goal) -> None:
    if not goal.performance_contract_id:
        return

    contract = await session.get(PerformanceContract, goal.performance_contract_id)
    if not contract:
        return

    contract_indicators = {
        indicator["name"]: indicator
        for indicator in contract.contract_data.get("indicators", [])
    }
    indicators_result = await session.execute(
        select(Indicator).where(
            Indicator.goal_id == goal.id,
            Indicator.deleted_at.is_(None),
        )
    )
    indicators = indicators_result.scalars().all()
    for indicator in indicators:
        ind_data = contract_indicators.get(indicator.name)
        if not ind_data:
            continue
        indicator.definition = plan_service._indicator_definition(ind_data)
        indicator.direction = plan_service._indicator_direction(ind_data)
        indicator.weight = ind_data.get("weight", 0) / 100.0
        indicator.target_value = ind_data.get("target")
        indicator.score_method = ScoreMethod.ratio
        indicator.redline = plan_service._is_redline_indicator(ind_data)

    await session.commit()


async def _close_conflicting_demo_periods(session, user_id: str, target_period_id: str) -> None:
    result = await session.execute(
        select(Period).where(
            Period.user_id == user_id,
            Period.status == PeriodStatus.open,
            Period.id != target_period_id,
            Period.name.like("%绩效演示周期%"),
            Period.deleted_at.is_(None),
        )
    )
    for period in result.scalars().all():
        period.status = PeriodStatus.closed
    await session.commit()


async def _ensure_contract_confirmed(session, user: User, period: Period) -> Goal:
    await _close_conflicting_demo_periods(session, user.id, period.id)

    existing_goal = await _get_existing_goal(session, user.id, period.id)
    if existing_goal:
        await _repair_existing_demo_goal(session, existing_goal)
        period.status = PeriodStatus.open
        await session.commit()
        return existing_goal

    analysis = await plan_service.create_job_analysis(
        session,
        current_user=user,
        user_id=user.id,
        jd_text=JD_CASES["S"]["jd"],
    )
    contract = await plan_service.generate_contract(
        session,
        current_user=user,
        period_id=period.id,
        user_id=user.id,
        job_analysis_id=analysis.id,
    )
    await plan_service.confirm_contract(
        session,
        current_user=user,
        contract_id=contract.id,
        confirmed_by=user.id,
    )

    goal = await _get_existing_goal(session, user.id, period.id)
    assert goal is not None, "No goal created after confirming contract"
    return goal


async def verify_p_stage_contract() -> None:
    _assert_mock_mode()
    await seed_demo_data()

    async with AsyncSessionLocal() as session:
        user = await _scalar_one(session, User, User.username == "demo_sales")
        period = await _scalar_one(
            session,
            Period,
            Period.user_id == user.id,
            Period.name == "2026年7月绩效演示周期",
            Period.deleted_at.is_(None),
        )

        goal = await _ensure_contract_confirmed(session, user, period)

        goals_result = await session.execute(
            select(Goal).where(
                Goal.owner_user_id == user.id,
                Goal.period_id == period.id,
                Goal.deleted_at.is_(None),
            )
        )
        goals = goals_result.scalars().all()
        assert len(goals) == 1, f"Expected one goal, got {len(goals)}"

        indicators_result = await session.execute(
            select(Indicator).where(
                Indicator.goal_id == goal.id,
                Indicator.deleted_at.is_(None),
            )
        )
        indicators = {indicator.name: indicator for indicator in indicators_result.scalars().all()}
        assert set(indicators) == set(EXPECTED_INDICATORS), sorted(indicators)

        for name, expected in EXPECTED_INDICATORS.items():
            indicator = indicators[name]
            assert abs(indicator.weight - expected["weight"]) < 0.001, (
                f"{name}: weight {indicator.weight}"
            )
            assert indicator.direction == expected["direction"], f"{name}: direction {indicator.direction}"
            assert indicator.redline == expected["redline"], f"{name}: redline {indicator.redline}"
            assert "目标：" in (indicator.definition or ""), f"{name}: missing target display metadata"
            assert "评分：" in (indicator.definition or ""), f"{name}: missing scoring metadata"

        await session.refresh(period)
        assert period.status == PeriodStatus.open, f"Expected period open, got {period.status}"

    print("P_STAGE_CONTRACT_OK")


if __name__ == "__main__":
    asyncio.run(verify_p_stage_contract())
