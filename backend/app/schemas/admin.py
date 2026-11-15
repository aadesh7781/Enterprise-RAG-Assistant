
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, EmailStr, ConfigDict


RoleName = Literal[
    "EMPLOYEE",
    "DEPARTMENT_ADMIN",
    "SUPER_ADMIN"
]


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
