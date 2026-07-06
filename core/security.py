import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from core.config import get_settings

settings = get_settings()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_COST)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def validate_password_strength(password: str) -> bool:
    return len(password) >= 6


def generate_jti() -> str:
    return str(uuid.uuid4())


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(
    *,
    user_id: str,
    username: str,
    role: str,
    department_id: str | None,
) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at)."""
    jti = generate_jti()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "department_id": department_id,
        "exp": expire,
        "iat": now,
        "jti": jti,
        "type": "access",
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti, expire


def create_refresh_token(*, user_id: str) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at)."""
    jti = generate_jti()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "jti": jti,
        "type": "refresh",
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti, expire


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def generate_reset_token() -> str:
    return os.urandom(32).hex()
