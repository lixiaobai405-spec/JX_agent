from datetime import datetime

from pydantic import BaseModel


class DepartmentCreate(BaseModel):
    name: str
    code: str
    parent_id: str | None = None
    manager_id: str | None = None
    description: str | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = None
    manager_id: str | None = None
    description: str | None = None


class DepartmentResponse(BaseModel):
    id: str
    name: str
    code: str
    parent_id: str | None
    level: int
    manager_id: str | None
    manager_name: str | None = None
    description: str | None = None
    member_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class DepartmentListResponse(BaseModel):
    total: int
    page: int
    limit: int
    data: list[DepartmentResponse]


class DepartmentTreeNode(BaseModel):
    id: str
    name: str
    level: int
    children: list["DepartmentTreeNode"] = []

    model_config = {"from_attributes": True}


DepartmentTreeNode.model_rebuild()


class DepartmentMember(BaseModel):
    id: str
    username: str
    full_name: str
    position_name: str | None = None


class DepartmentMembersResponse(BaseModel):
    department_id: str
    department_name: str
    members: list[DepartmentMember]
    total: int


class PositionCreate(BaseModel):
    name: str  # maps to title in DB
    code: str
    department_id: str | None = None
    level: str | None = None  # maps to job_level
    description: str | None = None
    responsibilities: list[str] | None = None


class PositionUpdate(BaseModel):
    name: str | None = None
    level: str | None = None
    department_id: str | None = None
    description: str | None = None
    responsibilities: list[str] | None = None


class PositionResponse(BaseModel):
    id: str
    name: str
    code: str
    level: str | None = None
    department_id: str | None
    department_name: str | None = None
    description: str | None = None
    member_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class PositionListResponse(BaseModel):
    total: int
    page: int
    limit: int
    data: list[PositionResponse]
