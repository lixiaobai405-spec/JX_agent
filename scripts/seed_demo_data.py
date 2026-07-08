import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import and_, select

from core.database import AsyncSessionLocal, init_db
from core.security import get_password_hash, verify_password
from models.organization import Department, Position
from models.period import Period, PeriodStatus
from models.user import User, UserRole, UserStatus


DEMO_PASSWORD = "Demo@123456"


JD_CASES = {
    "S": {
        "username": "demo_sales",
        "label": "华东KA销售经理",
        "jd": """负责华东区全家、罗森等便利系统的年度及月度销售目标达成，确保及时回款。
严格执行公司巡店SOP，检查货架陈列、价格签及促销物料。
负责新品“果气森林”的上架铺货，提升核心门店入店率。
坚决杜绝线下乱价和跨区串货行为，维护公司价格体系。
每周五需提交区域销售复盘报告。""",
    },
    "P": {
        "username": "demo_rd",
        "label": "气泡水研发高级工程师",
        "jd": """负责气泡水新口味的研发，从实验室配方到中试生产，确保项目按计划推进。
以长周期项目制跟进，需确保新产品的口感盲测达到行业标准。
优化现有产品配方，持续降低单瓶原材料成本。
积极沉淀研发成果，撰写规范的技术文档并申请产品专利。
需与生产部门紧密协作，顺利完成产品转产。
严格把控研发阶段的食品安全，按研发节点进行双周汇报。""",
    },
    "O": {
        "username": "demo_ops",
        "label": "饮料灌装线线长",
        "jd": """负责气泡水灌装线的日常排班与生产运营，保障每日产量达成。
严格遵循食品安全标准与生产SOP作业指导书。
有效控制设备异常停机时间，并严格把控产品次品率。
维护生产车间的6S现场环境卫生。
每日进行晨会，复盘昨日生产与质量数据。""",
    },
    "F": {
        "username": "demo_recruiter",
        "label": "华东区招聘专员",
        "jd": """负责华东销售团队的日常招聘与入职手续办理。
快速响应业务部门的高频用人需求，保障人员到岗率。
拓展简历库并合理管控各大招聘渠道的使用费用。
具备良好的服务意识，优化应聘流程，确保候选人体验。
妥善保管员工档案资料，严防隐私数据泄露。
每周统计招聘漏斗转化数据并进行汇报。""",
    },
    "M": {
        "username": "demo_supply",
        "label": "供应链总监",
        "jd": """统筹公司整体供应链管理（含采购、生产车间、仓储物流）。
制定供应链中长期战略规划，如主导仓储自动化等重大项目。
持续优化端到端供应链流程，降低综合交付成本，提升库存周转率。
考核并提升核心供应商的交付质量达标率。
负责供应链管理团队的梯队建设、继任者培养与人才赋能。
严守商业底线，杜绝寻源采购过程中的任何违规行为。
每月定期向CEO进行经营管理分析汇报。""",
    },
}


DEPARTMENTS = [
    {"code": "DEMO_COMPANY", "name": "乐饮食品有限公司", "parent": None},
    {"code": "DEMO_SALES_EAST", "name": "华东销售部", "parent": "DEMO_COMPANY"},
    {"code": "DEMO_RND", "name": "研发中心", "parent": "DEMO_COMPANY"},
    {"code": "DEMO_FACTORY", "name": "生产运营部", "parent": "DEMO_COMPANY"},
    {"code": "DEMO_HR", "name": "人力资源部", "parent": "DEMO_COMPANY"},
    {"code": "DEMO_SUPPLY", "name": "供应链中心", "parent": "DEMO_COMPANY"},
]


POSITIONS = [
    {"code": "DEMO_CEO", "title": "CEO", "department": "DEMO_COMPANY"},
    {"code": "DEMO_SALES_MANAGER", "title": "华东销售部负责人", "department": "DEMO_SALES_EAST"},
    {"code": "DEMO_KA_SALES", "title": "华东KA销售经理", "department": "DEMO_SALES_EAST"},
    {"code": "DEMO_RND_ENGINEER", "title": "气泡水研发高级工程师", "department": "DEMO_RND"},
    {"code": "DEMO_LINE_LEADER", "title": "饮料灌装线线长", "department": "DEMO_FACTORY"},
    {"code": "DEMO_RECRUITER", "title": "华东区招聘专员", "department": "DEMO_HR"},
    {"code": "DEMO_SUPPLY_DIRECTOR", "title": "供应链总监", "department": "DEMO_SUPPLY"},
]


USERS = [
    {"username": "demo_ceo", "role": UserRole.system_admin, "full_name": "周总", "position": "DEMO_CEO", "department": "DEMO_COMPANY", "manager": None},
    {"username": "demo_manager", "role": UserRole.manager, "full_name": "李娜", "position": "DEMO_SALES_MANAGER", "department": "DEMO_SALES_EAST", "manager": "demo_ceo"},
    {"username": "demo_sales", "role": UserRole.employee, "full_name": "王强", "position": "DEMO_KA_SALES", "department": "DEMO_SALES_EAST", "manager": "demo_manager"},
    {"username": "demo_rd", "role": UserRole.employee, "full_name": "陈晨", "position": "DEMO_RND_ENGINEER", "department": "DEMO_RND", "manager": "demo_ceo"},
    {"username": "demo_ops", "role": UserRole.employee, "full_name": "赵磊", "position": "DEMO_LINE_LEADER", "department": "DEMO_FACTORY", "manager": "demo_ceo"},
    {"username": "demo_recruiter", "role": UserRole.employee, "full_name": "孙敏", "position": "DEMO_RECRUITER", "department": "DEMO_HR", "manager": "demo_manager"},
    {"username": "demo_supply", "role": UserRole.manager, "full_name": "吴昊", "position": "DEMO_SUPPLY_DIRECTOR", "department": "DEMO_SUPPLY", "manager": "demo_ceo"},
]


PERIODS = [
    {"username": "demo_sales", "name": "2026年7月绩效演示周期", "start": "2026-07-01T00:00:00+00:00", "end": "2026-07-31T23:59:59+00:00"},
    {"username": "demo_ops", "name": "2026年7月绩效演示周期", "start": "2026-07-01T00:00:00+00:00", "end": "2026-07-31T23:59:59+00:00"},
    {"username": "demo_recruiter", "name": "2026年7月绩效演示周期", "start": "2026-07-01T00:00:00+00:00", "end": "2026-07-31T23:59:59+00:00"},
    {"username": "demo_rd", "name": "2026年Q3绩效演示周期", "start": "2026-07-01T00:00:00+00:00", "end": "2026-09-30T23:59:59+00:00"},
    {"username": "demo_supply", "name": "2026年下半年绩效演示周期", "start": "2026-07-01T00:00:00+00:00", "end": "2026-12-31T23:59:59+00:00"},
]


@dataclass
class Counters:
    created: int = 0
    updated: int = 0

    def add_created(self) -> None:
        self.created += 1

    def add_updated(self) -> None:
        self.updated += 1


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc).replace(tzinfo=None)


def _set_if_changed(obj: object, field: str, value: object) -> bool:
    if getattr(obj, field) != value:
        setattr(obj, field, value)
        return True
    return False


async def _one(session, model, *conditions):
    result = await session.execute(select(model).where(and_(*conditions)))
    return result.scalar_one_or_none()


async def seed_departments(session) -> tuple[dict[str, Department], Counters]:
    counters = Counters()
    departments: dict[str, Department] = {}

    for row in DEPARTMENTS:
        parent = departments.get(row["parent"]) if row["parent"] else None
        department = await _one(session, Department, Department.code == row["code"])
        if not department:
            department = Department(
                code=row["code"],
                name=row["name"],
                parent_id=parent.id if parent else None,
                level=(parent.level + 1) if parent else 1,
                path=f"{parent.path}{row['code']}/" if parent else f"/{row['code']}/",
                is_active=True,
            )
            session.add(department)
            await session.flush()
            counters.add_created()
        else:
            changed = False
            changed |= _set_if_changed(department, "name", row["name"])
            changed |= _set_if_changed(department, "parent_id", parent.id if parent else None)
            changed |= _set_if_changed(department, "level", (parent.level + 1) if parent else 1)
            changed |= _set_if_changed(department, "path", f"{parent.path}{row['code']}/" if parent else f"/{row['code']}/")
            changed |= _set_if_changed(department, "is_active", True)
            if changed:
                counters.add_updated()
        departments[row["code"]] = department

    return departments, counters


async def seed_positions(session, departments: dict[str, Department]) -> tuple[dict[str, Position], Counters]:
    counters = Counters()
    positions: dict[str, Position] = {}

    for row in POSITIONS:
        department = departments[row["department"]]
        position = await _one(session, Position, Position.code == row["code"])
        if not position:
            position = Position(
                code=row["code"],
                title=row["title"],
                department_id=department.id,
                is_active=True,
            )
            session.add(position)
            await session.flush()
            counters.add_created()
        else:
            changed = False
            changed |= _set_if_changed(position, "title", row["title"])
            changed |= _set_if_changed(position, "department_id", department.id)
            changed |= _set_if_changed(position, "is_active", True)
            if changed:
                counters.add_updated()
        positions[row["code"]] = position

    return positions, counters


async def seed_users(session, departments: dict[str, Department], positions: dict[str, Position]) -> tuple[dict[str, User], Counters]:
    counters = Counters()
    users: dict[str, User] = {}

    for row in USERS:
        user = await _one(session, User, User.username == row["username"])
        department = departments[row["department"]]
        position = positions[row["position"]]
        email = f"{row['username']}@example.com"
        if not user:
            user = User(
                username=row["username"],
                email=email,
                full_name=row["full_name"],
                role=row["role"],
                hashed_password=get_password_hash(DEMO_PASSWORD),
                status=UserStatus.active,
                department_id=department.id,
                position_id=position.id,
            )
            session.add(user)
            await session.flush()
            counters.add_created()
        else:
            changed = False
            changed |= _set_if_changed(user, "email", email)
            changed |= _set_if_changed(user, "full_name", row["full_name"])
            changed |= _set_if_changed(user, "role", row["role"])
            changed |= _set_if_changed(user, "status", UserStatus.active)
            changed |= _set_if_changed(user, "department_id", department.id)
            changed |= _set_if_changed(user, "position_id", position.id)
            if not user.hashed_password or not verify_password(DEMO_PASSWORD, user.hashed_password):
                user.hashed_password = get_password_hash(DEMO_PASSWORD)
                changed = True
            if changed:
                counters.add_updated()
        users[row["username"]] = user

    for row in USERS:
        user = users[row["username"]]
        manager = users.get(row["manager"]) if row["manager"] else None
        if _set_if_changed(user, "manager_id", manager.id if manager else None):
            counters.add_updated()

    return users, counters


async def seed_periods(session, users: dict[str, User]) -> Counters:
    counters = Counters()
    for row in PERIODS:
        user = users[row["username"]]
        period = await _one(
            session,
            Period,
            Period.user_id == user.id,
            Period.name == row["name"],
            Period.deleted_at.is_(None),
        )
        if not period:
            period = Period(
                user_id=user.id,
                name=row["name"],
                start_date=_dt(row["start"]),
                end_date=_dt(row["end"]),
                status=PeriodStatus.draft,
                d_phase_completed=False,
            )
            session.add(period)
            await session.flush()
            counters.add_created()
        else:
            changed = False
            changed |= _set_if_changed(period, "start_date", _dt(row["start"]))
            changed |= _set_if_changed(period, "end_date", _dt(row["end"]))
            if changed:
                counters.add_updated()
    return counters


async def seed_demo_data() -> None:
    await init_db()
    async with AsyncSessionLocal() as session:
        departments, dept_counts = await seed_departments(session)
        positions, pos_counts = await seed_positions(session, departments)
        users, user_counts = await seed_users(session, departments, positions)
        period_counts = await seed_periods(session, users)
        await session.commit()

    print(
        "demo_seed_summary "
        f"departments={dept_counts.created}/{dept_counts.updated} "
        f"positions={pos_counts.created}/{pos_counts.updated} "
        f"users={user_counts.created}/{user_counts.updated} "
        f"periods={period_counts.created}/{period_counts.updated}"
    )
    for code, case in JD_CASES.items():
        print(f"JD_CASE {code} {case['username']} {case['label']}")
    print("DEMO_SEED_OK")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
