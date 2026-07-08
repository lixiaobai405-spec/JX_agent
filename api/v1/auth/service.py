import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.exceptions import (
    AccountDisabledError,
    InvalidCredentialsError,
    ResetTokenInvalidError,
    SessionAccessDeniedError,
    SessionNotFoundError,
    TokenInvalidError,
    TokenRevokedError,
    WeakPasswordError,
    WrongPasswordError,
)
from core.security import (
    create_access_token,
    create_refresh_token,
    generate_reset_token,
    get_password_hash,
    hash_token,
    validate_password_strength,
    verify_password,
)
from models.token import BlacklistedAccessToken, PasswordResetToken, RefreshToken
from models.user import User, UserStatus

settings = get_settings()


async def login(
    db: AsyncSession,
    username: str,
    password: str,
    ip_address: str | None = None,
    device_info: dict | None = None,
) -> dict:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError()
    if user.status != UserStatus.active:
        raise AccountDisabledError()

    # Enforce max sessions: revoke oldest if over limit
    active_sessions = await db.execute(
        select(RefreshToken)
        .where(
            and_(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        .order_by(RefreshToken.created_at.asc())
    )
    sessions = active_sessions.scalars().all()
    if len(sessions) >= settings.MAX_SESSIONS:
        for old in sessions[: len(sessions) - settings.MAX_SESSIONS + 1]:
            old.revoked_at = datetime.now(timezone.utc)

    access_token, _, expires_at = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role.value,
        department_id=user.department_id,
    )
    refresh_token_str, refresh_jti, refresh_expires = create_refresh_token(user_id=user.id)

    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token_str),
        jti=refresh_jti,
        device_info=json.dumps(device_info) if device_info else None,
        ip_address=ip_address,
        expires_at=refresh_expires,
    ))

    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "token_type": "Bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user,
    }


async def refresh_tokens(db: AsyncSession, refresh_token_str: str) -> dict:
    from core.security import decode_token
    from jose import JWTError

    try:
        payload = decode_token(refresh_token_str)
    except JWTError:
        raise TokenInvalidError()

    if payload.get("type") != "refresh":
        raise TokenInvalidError("Wrong token type")

    token_hash = hash_token(refresh_token_str)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token_row = result.scalar_one_or_none()

    if not token_row or token_row.revoked_at:
        raise TokenRevokedError()

    # 确保 expires_at 是 timezone-aware
    expires_at = token_row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise TokenInvalidError()

    user = await db.get(User, token_row.user_id)
    if not user or user.status != UserStatus.active:
        raise AccountDisabledError()

    # Token rotation: revoke old
    token_row.revoked_at = datetime.now(timezone.utc)

    access_token, _, _ = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role.value,
        department_id=user.department_id,
    )
    new_refresh_str, new_refresh_jti, new_refresh_expires = create_refresh_token(user_id=user.id)

    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_refresh_str),
        jti=new_refresh_jti,
        device_info=token_row.device_info,
        ip_address=token_row.ip_address,
        expires_at=new_refresh_expires,
    ))
    await db.flush()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_str,
        "token_type": "Bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def logout(
    db: AsyncSession,
    user: User,
    access_jti: str,
    access_exp: datetime,
    refresh_token_str: str | None = None,
) -> None:
    db.add(BlacklistedAccessToken(
        jti=access_jti,
        user_id=user.id,
        expires_at=access_exp,
    ))
    if refresh_token_str:
        token_hash = hash_token(refresh_token_str)
        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user.id,
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.revoked_at.is_(None),
                )
            )
        )
        token_row = result.scalar_one_or_none()
        if token_row:
            token_row.revoked_at = datetime.now(timezone.utc)
    await db.flush()


async def change_password(
    db: AsyncSession, user: User, old_password: str, new_password: str
) -> None:
    if not verify_password(old_password, user.hashed_password):
        raise WrongPasswordError()
    if not validate_password_strength(new_password):
        raise WeakPasswordError()

    user.hashed_password = get_password_hash(new_password)
    user.tokens_invalidated_at = datetime.now(timezone.utc)

    # Revoke all refresh tokens
    result = await db.execute(
        select(RefreshToken).where(
            and_(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        )
    )
    for rt in result.scalars().all():
        rt.revoked_at = datetime.now(timezone.utc)
    await db.flush()


async def request_password_reset(db: AsyncSession, email: str) -> str:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        # Return silently to avoid email enumeration
        return ""

    raw_token = generate_reset_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=expires,
    ))
    await db.flush()
    return raw_token


async def confirm_password_reset(db: AsyncSession, token: str, new_password: str) -> None:
    if not validate_password_strength(new_password):
        raise WeakPasswordError()

    token_hash = hash_token(token)
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    token_row = result.scalar_one_or_none()

    if not token_row or token_row.used_at or token_row.expires_at < datetime.now(timezone.utc):
        raise ResetTokenInvalidError()

    user = await db.get(User, token_row.user_id)
    if not user:
        raise ResetTokenInvalidError()

    user.hashed_password = get_password_hash(new_password)
    user.tokens_invalidated_at = datetime.now(timezone.utc)
    token_row.used_at = datetime.now(timezone.utc)

    # Revoke all refresh tokens
    result = await db.execute(
        select(RefreshToken).where(
            and_(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        )
    )
    for rt in result.scalars().all():
        rt.revoked_at = datetime.now(timezone.utc)
    await db.flush()


async def get_sessions(db: AsyncSession, user: User, current_jti: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshToken).where(
            and_(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        ).order_by(RefreshToken.created_at.desc())
    )
    sessions = []
    for rt in result.scalars().all():
        device = json.loads(rt.device_info) if rt.device_info else None
        sessions.append({
            "id": rt.id,
            "device_info": device,
            "ip_address": rt.ip_address,
            "created_at": rt.created_at,
            "expires_at": rt.expires_at,
            "is_current": rt.jti == current_jti,
        })
    return sessions


async def revoke_session(db: AsyncSession, user: User, session_id: str) -> None:
    rt = await db.get(RefreshToken, session_id)
    if not rt:
        raise SessionNotFoundError()
    if rt.user_id != user.id:
        raise SessionAccessDeniedError()
    rt.revoked_at = datetime.now(timezone.utc)
    await db.flush()
