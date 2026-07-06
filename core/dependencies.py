from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import (
    AccountDisabledError,
    PermissionDeniedError,
    TokenInvalidError,
    TokenRevokedError,
)
from core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from models.token import BlacklistedAccessToken
    from models.user import User

    try:
        payload = decode_token(token)
    except JWTError:
        raise TokenInvalidError()

    if payload.get("type") != "access":
        raise TokenInvalidError("Wrong token type")

    user_id: str | None = payload.get("sub")
    jti: str | None = payload.get("jti")
    iat: int | None = payload.get("iat")

    if not user_id or not jti:
        raise TokenInvalidError()

    # Check JTI blacklist
    blacklisted = await db.get(BlacklistedAccessToken, jti)
    if blacklisted:
        raise TokenRevokedError()

    user = await db.get(User, user_id)
    if not user:
        raise TokenInvalidError()

    # Check bulk token invalidation (password change/reset)
    if user.tokens_invalidated_at and iat:
        token_iat = datetime.fromtimestamp(iat, tz=timezone.utc)
        if token_iat < user.tokens_invalidated_at:
            raise TokenRevokedError()

    return user


async def get_current_active_user(user=Depends(get_current_user)):
    from models.user import UserStatus
    if user.status != UserStatus.active:
        raise AccountDisabledError()
    return user


CurrentUser = Annotated[object, Depends(get_current_active_user)]


def require_roles(*allowed_roles: str):
    async def checker(user=Depends(get_current_active_user)):
        if user.role.value not in allowed_roles:
            raise PermissionDeniedError(f"Requires one of: {', '.join(allowed_roles)}")
        return user
    return checker
