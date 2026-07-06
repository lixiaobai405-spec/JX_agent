from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.plan_phase import JobPrototype, StrategyMatrix


async def get_prototype_config(db: AsyncSession, code: str) -> dict:
    """从数据库读取岗位原型配置"""
    proto_result = await db.execute(
        select(JobPrototype).where(JobPrototype.code == code)
    )
    proto = proto_result.scalar_one_or_none()
    if not proto:
        raise ValueError(f"Prototype {code} not found")

    strategies_result = await db.execute(
        select(StrategyMatrix).where(StrategyMatrix.job_prototype_code == code)
    )
    strategies = strategies_result.scalars().all()

    strategy_dict = {}
    for s in strategies:
        strategy_dict[s.dimension] = s.configuration

    return {
        "name": f"{proto.code}类（{proto.name}）",
        "description": proto.description or "",
        "assessment_period": strategy_dict.get("考核周期", {}).get("cycle", "月度"),
        "indicator_count": f"{proto.indicator_count_min}-{proto.indicator_count_max}个",
        "quantitative_ratio": f"定量指标 {int(proto.quantitative_ratio_min*100)}-{int(proto.quantitative_ratio_max*100)}%",
        "coaching": strategy_dict.get("辅导周期", {}).get("cycle", "月度"),
        "result_application": "挂钩绩效奖金",
        "redline_required": True,
    }
