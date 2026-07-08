import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import and_, select

from core.database import AsyncSessionLocal
from models.organization import Department, Position
from models.period import Period
from models.user import User
from scripts.seed_demo_data import DEPARTMENTS, PERIODS, POSITIONS, USERS


async def _one(session, model, *conditions):
    result = await session.execute(select(model).where(and_(*conditions)))
    return result.scalar_one_or_none()


async def verify_demo_data() -> None:
    async with AsyncSessionLocal() as session:
        departments: dict[str, Department] = {}
        for row in DEPARTMENTS:
            department = await _one(session, Department, Department.code == row["code"], Department.deleted_at.is_(None))
            assert department, f"missing department {row['code']}"
            departments[row["code"]] = department

        positions: dict[str, Position] = {}
        for row in POSITIONS:
            position = await _one(session, Position, Position.code == row["code"], Position.deleted_at.is_(None))
            assert position, f"missing position {row['code']}"
            assert position.department_id == departments[row["department"]].id, f"position department mismatch {row['code']}"
            positions[row["code"]] = position

        users: dict[str, User] = {}
        for row in USERS:
            user = await _one(session, User, User.username == row["username"], User.deleted_at.is_(None))
            assert user, f"missing user {row['username']}"
            assert user.hashed_password, f"empty hashed_password {row['username']}"
            assert user.department_id == departments[row["department"]].id, f"user department mismatch {row['username']}"
            assert user.position_id == positions[row["position"]].id, f"user position mismatch {row['username']}"
            users[row["username"]] = user

        for row in USERS:
            user = users[row["username"]]
            manager = users.get(row["manager"]) if row["manager"] else None
            assert user.manager_id == (manager.id if manager else None), f"manager mismatch {row['username']}"

        for row in PERIODS:
            user = users[row["username"]]
            period = await _one(
                session,
                Period,
                Period.user_id == user.id,
                Period.name == row["name"],
                Period.deleted_at.is_(None),
            )
            assert period, f"missing period {row['username']} {row['name']}"

    print("DEMO_VERIFY_OK")


if __name__ == "__main__":
    asyncio.run(verify_demo_data())
