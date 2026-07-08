import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.v1.auth import service
from core.database import Base
from core.security import hash_token
from models.token import BlacklistedAccessToken, RefreshToken
from models.user import User, UserRole

# Import models with foreign keys referenced by the tables under test.
import models.organization  # noqa: F401


class AuthLogoutTest(unittest.IsolatedAsyncioTestCase):
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

    async def _seed_user_with_refresh_tokens(self, session: AsyncSession):
        now = datetime.now(timezone.utc)
        user = User(
            id="user-1",
            username="demo_user",
            full_name="测试用户",
            email="demo@example.com",
            hashed_password="hashed",
            role=UserRole.employee,
        )
        current = RefreshToken(
            id="refresh-current",
            user_id=user.id,
            token_hash=hash_token("current-refresh-token"),
            jti="current-jti",
            expires_at=now + timedelta(days=1),
        )
        other = RefreshToken(
            id="refresh-other",
            user_id=user.id,
            token_hash=hash_token("other-refresh-token"),
            jti="other-jti",
            expires_at=now + timedelta(days=1),
        )
        session.add_all([user, current, other])
        await session.commit()
        return user

    async def test_logout_revokes_only_matching_refresh_token(self):
        async with self.Session() as session:
            user = await self._seed_user_with_refresh_tokens(session)
            access_exp = datetime.now(timezone.utc) + timedelta(minutes=15)

            await service.logout(
                db=session,
                user=user,
                access_jti="access-jti",
                access_exp=access_exp,
                refresh_token_str="current-refresh-token",
            )

            current = await session.get(RefreshToken, "refresh-current")
            other = await session.get(RefreshToken, "refresh-other")
            blacklisted = await session.get(BlacklistedAccessToken, "access-jti")

            self.assertIsNotNone(current.revoked_at)
            self.assertIsNone(other.revoked_at)
            self.assertIsNotNone(blacklisted)

    async def test_logout_without_refresh_token_keeps_refresh_sessions(self):
        async with self.Session() as session:
            user = await self._seed_user_with_refresh_tokens(session)

            await service.logout(
                db=session,
                user=user,
                access_jti="access-jti",
                access_exp=datetime.now(timezone.utc) + timedelta(minutes=15),
            )

            result = await session.execute(select(RefreshToken))
            refresh_tokens = result.scalars().all()
            self.assertTrue(all(token.revoked_at is None for token in refresh_tokens))


if __name__ == "__main__":
    unittest.main()
