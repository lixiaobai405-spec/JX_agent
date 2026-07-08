from datetime import datetime

from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 900


class LoginResponse(TokenResponse):
    user: "UserBrief"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        from core.security import validate_password_strength
        if not validate_password_strength(v):
            from core.exceptions import WeakPasswordError
            raise WeakPasswordError()
        return v


class ResetPasswordRequest(BaseModel):
    email: str


class ResetPasswordConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        from core.security import validate_password_strength
        if not validate_password_strength(v):
            from core.exceptions import WeakPasswordError
            raise WeakPasswordError()
        return v


class DeviceInfo(BaseModel):
    browser: str | None = None
    os: str | None = None
    device_type: str | None = None


class SessionResponse(BaseModel):
    id: str
    device_info: DeviceInfo | None
    ip_address: str | None
    created_at: datetime
    expires_at: datetime
    is_current: bool


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


class MessageResponse(BaseModel):
    message: str


class UserBrief(BaseModel):
    id: str
    username: str
    email: str
    role: str
    department_id: str | None

    model_config = {"from_attributes": True}


LoginResponse.model_rebuild()
