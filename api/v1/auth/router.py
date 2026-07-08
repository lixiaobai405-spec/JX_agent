from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.auth import schemas, service
from core.database import get_db
from core.dependencies import CurrentUser, get_current_active_user
from core.security import decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.LoginResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    ip = request.client.host if request and request.client else None
    result = await service.login(
        db=db,
        username=form.username,
        password=form.password,
        ip_address=ip,
    )
    return schemas.LoginResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
        user=schemas.UserBrief.model_validate(result["user"]),
    )


@router.post("/refresh", response_model=schemas.TokenResponse)
async def refresh(body: schemas.RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await service.refresh_tokens(db=db, refresh_token_str=body.refresh_token)
    return schemas.TokenResponse(**result)


@router.post("/logout", response_model=schemas.MessageResponse)
async def logout(
    request: Request,
    body: schemas.LogoutRequest | None = Body(default=None),
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.security import OAuth2PasswordBearer
    from jose import JWTError

    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
        jti = payload["jti"]
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    except (JWTError, KeyError):
        jti = ""
        exp = datetime.now(timezone.utc)

    await service.logout(
        db=db,
        user=current_user,
        access_jti=jti,
        access_exp=exp,
        refresh_token_str=body.refresh_token if body else None,
    )
    return {"message": "Successfully logged out"}


@router.get("/me")
async def me(current_user=Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from models.organization import Department, Position
    from models.user import User

    dept_name = None
    if current_user.department_id:
        dept = await db.get(Department, current_user.department_id)
        dept_name = dept.name if dept else None

    pos_name = None
    if current_user.position_id:
        pos = await db.get(Position, current_user.position_id)
        pos_name = pos.title if pos else None

    manager_name = None
    if current_user.manager_id:
        mgr = await db.get(User, current_user.manager_id)
        manager_name = mgr.full_name if mgr else None

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "department_id": current_user.department_id,
        "department_name": dept_name,
        "position_id": current_user.position_id,
        "position_name": pos_name,
        "manager_id": current_user.manager_id,
        "manager_name": manager_name,
        "created_at": current_user.created_at,
        "last_login_at": current_user.last_login_at,
    }


@router.post("/password/change", response_model=schemas.MessageResponse)
async def change_password(
    body: schemas.ChangePasswordRequest,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await service.change_password(
        db=db, user=current_user,
        old_password=body.old_password, new_password=body.new_password,
    )
    return {"message": "Password changed successfully"}


@router.post("/password/reset-request", response_model=schemas.MessageResponse)
async def reset_request(body: schemas.ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    await service.request_password_reset(db=db, email=body.email)
    return {"message": "Password reset email sent"}


@router.post("/password/reset-confirm", response_model=schemas.MessageResponse)
async def reset_confirm(body: schemas.ResetPasswordConfirm, db: AsyncSession = Depends(get_db)):
    await service.confirm_password_reset(db=db, token=body.token, new_password=body.new_password)
    return {"message": "Password reset successfully"}


@router.get("/sessions", response_model=schemas.SessionListResponse)
async def list_sessions(
    request: Request,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
        current_jti = payload.get("jti", "")
    except Exception:
        current_jti = ""

    sessions = await service.get_sessions(db=db, user=current_user, current_jti=current_jti)
    return {"sessions": sessions}


@router.delete("/sessions/{session_id}", response_model=schemas.MessageResponse)
async def revoke_session(
    session_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await service.revoke_session(db=db, user=current_user, session_id=session_id)
    return {"message": "Session revoked successfully"}
