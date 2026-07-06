from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import get_settings

settings = get_settings()

_connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def seed_job_prototypes() -> None:
    from sqlalchemy import select
    from models.plan_phase import JobPrototype

    prototypes_data = [
        {"code": "S", "name": "铁军型", "description": "业绩导向，结果可量化", "quantifiability_min": 8, "quantifiability_max": 10, "output_cycle_min": 0, "output_cycle_max": 3, "work_nature_min": 8, "work_nature_max": 10, "indicator_count_min": 3, "indicator_count_max": 5, "quantitative_ratio_min": 0.80, "quantitative_ratio_max": 1.00, "primary_target_setting": "自上而下"},
        {"code": "P", "name": "项目型", "description": "创造性工作，长周期", "quantifiability_min": 0, "quantifiability_max": 4, "output_cycle_min": 7, "output_cycle_max": 10, "work_nature_min": 0, "work_nature_max": 4, "indicator_count_min": 5, "indicator_count_max": 7, "quantitative_ratio_min": 0.40, "quantitative_ratio_max": 0.60, "primary_target_setting": "混合（自我设定为辅）"},
        {"code": "O", "name": "运营型", "description": "标准化流程，高量化", "quantifiability_min": 8, "quantifiability_max": 10, "output_cycle_min": 0, "output_cycle_max": 3, "work_nature_min": 8, "work_nature_max": 10, "indicator_count_min": 4, "indicator_count_max": 5, "quantitative_ratio_min": 0.90, "quantitative_ratio_max": 1.00, "primary_target_setting": "历史推导"},
        {"code": "F", "name": "职能型", "description": "服务响应，低量化", "quantifiability_min": 0, "quantifiability_max": 4, "output_cycle_min": 0, "output_cycle_max": 3, "work_nature_min": 5, "work_nature_max": 7, "indicator_count_min": 5, "indicator_count_max": 7, "quantitative_ratio_min": 0.50, "quantitative_ratio_max": 0.65, "primary_target_setting": "混合（自我设定为辅）"},
        {"code": "M", "name": "管理型", "description": "战略规划，长周期", "quantifiability_min": 0, "quantifiability_max": 4, "output_cycle_min": 7, "output_cycle_max": 10, "work_nature_min": 0, "work_nature_max": 4, "indicator_count_min": 5, "indicator_count_max": 6, "quantitative_ratio_min": 0.50, "quantitative_ratio_max": 0.70, "primary_target_setting": "自上而下"},
    ]

    async with AsyncSessionLocal() as session:
        for proto_data in prototypes_data:
            result = await session.execute(select(JobPrototype).where(JobPrototype.code == proto_data["code"]))
            if not result.scalar_one_or_none():
                prototype = JobPrototype(**proto_data)
                session.add(prototype)
        await session.commit()


async def seed_strategy_matrices() -> None:
    from sqlalchemy import select
    from models.plan_phase import StrategyMatrix

    strategies_data = [
        {"job_prototype_code": "S", "dimension": "指标来源", "configuration": {"sources": ["业绩结果KPI", "关键任务"]}, "priority": 1},
        {"job_prototype_code": "S", "dimension": "评价人", "configuration": {"evaluators": ["直属上级", "系统数据"]}, "priority": 1},
        {"job_prototype_code": "S", "dimension": "指标属性", "configuration": {"type": "定量为主（>80%）"}, "priority": 1},
        {"job_prototype_code": "S", "dimension": "指标维度", "configuration": {"dimensions": ["业绩产出"]}, "priority": 1},
        {"job_prototype_code": "S", "dimension": "目标值设定", "configuration": {"methods": ["自上而下"]}, "priority": 1},
        {"job_prototype_code": "S", "dimension": "考核周期", "configuration": {"cycle": "monthly"}, "priority": 1},
        {"job_prototype_code": "S", "dimension": "辅导周期", "configuration": {"cycle": "weekly"}, "priority": 1},
        {"job_prototype_code": "S", "dimension": "结果应用", "configuration": {"applications": ["绩效奖金系数"]}, "priority": 1},
    ]

    async with AsyncSessionLocal() as session:
        for strategy_data in strategies_data:
            result = await session.execute(
                select(StrategyMatrix).where(
                    (StrategyMatrix.job_prototype_code == strategy_data["job_prototype_code"]) &
                    (StrategyMatrix.dimension == strategy_data["dimension"])
                )
            )
            if not result.scalar_one_or_none():
                strategy = StrategyMatrix(**strategy_data)
                session.add(strategy)
        await session.commit()


async def init_db() -> None:
    from sqlalchemy import select
    from models.user import User, UserRole
    from core.security import get_password_hash

    # Import all models so their tables are registered on Base.metadata
    import models.organization  # noqa: F401
    import models.token  # noqa: F401
    import models.period  # noqa: F401
    import models.plan_phase  # noqa: F401
    import models.check_phase  # noqa: F401
    import models.do_phase  # noqa: F401
    import models.action_phase  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create default admin user if not exists
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
            admin = User(
                username="admin",
                email="admin@example.com",
                full_name="System Administrator",
                hashed_password=get_password_hash("admin"),
                role=UserRole.system_admin,
            )
            session.add(admin)
            await session.commit()

    # Seed job prototypes and strategy matrices
    await seed_job_prototypes()
    await seed_strategy_matrices()
