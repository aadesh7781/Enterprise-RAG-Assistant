
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, ConfigDict


RoleName = Literal[
    "EMPLOYEE",
    "DEPARTMENT_ADMIN",
    "SUPER_ADMIN"
]


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=12, max_length=128)
    department_id: UUID | None = None
    role_name: RoleName = "EMPLOYEE"

    model_config = ConfigDict(extra="forbid")


class RoleAssignmentRequest(BaseModel):
    role_name: RoleName

    model_config = ConfigDict(extra="forbid")


class DepartmentAssignmentRequest(BaseModel):
    department_id: UUID

    model_config = ConfigDict(extra="forbid")


class UserRolesResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    roles: list[str]


class DepartmentResponse(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)
