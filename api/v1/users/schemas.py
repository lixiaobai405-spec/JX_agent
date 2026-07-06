from datetime import date, datetime

from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str
    role: str = "employee"
    department_id: str | None = None
    position_id: str | None = None
    manager_id: str | None = None
    hire_date: date | None = None
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        from core.security import validate_password_strength
        if not validate_password_strength(v):
            from core.exceptions import WeakPasswordError
            raise WeakPasswordError()
        return v


class UserUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = None
    phone: str | None = None
    department_id: str | None = None
    position_id: str | None = None
    manager_id: str | None = None
    role: str | None = None
    status: str | None = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    status: str
    department_id: str | None
    department_name: str | None = None
    position_id: str | None
    position_name: str | None = None
    manager_id: str | None
    manager_name: str | None = None
    hire_date: datetime | None = None
    phone: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    total: int
    page: int
    limit: int
    pages: int
    data: list[UserResponse]


class SubordinateItem(BaseModel):
    id: str
    username: str
    full_name: str
    role: str
    department_name: str | None = None
    position_name: str | None = None
    is_direct: bool
    level: int


class SubordinatesResponse(BaseModel):
    user_id: str
    user_name: str
    subordinates: list[SubordinateItem]
    total: int


class TeamResponse(BaseModel):
    manager: dict
    team_members: list[dict]
    total_members: int
