
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import User, Role, Department
from app.schemas.auth import UserResponse
from app.schemas.admin import (
    RoleAssignmentRequest,
    DepartmentAssignmentRequest,
    UserRolesResponse,
    RoleName
)
from app.security.permissions import require_roles


router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Administration"]
)


# --------------------------------------------------
# SUPER ADMIN TEST
# --------------------------------------------------

@router.get("/test")
def admin_test(
    current_user: User = Depends(
        require_roles("SUPER_ADMIN")
    )
):
    return {
        "message": "Admin access granted",
        "user": current_user.email
    }


# --------------------------------------------------
# VIEW ALL USERS - SUPER ADMIN
# --------------------------------------------------

@router.get("/users", response_model=list[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("SUPER_ADMIN")
    )
):
    return db.scalars(
        select(User).order_by(User.email)
    ).all()


# --------------------------------------------------
# ASSIGN ROLE - SUPER ADMIN
# --------------------------------------------------

@router.post(
    "/users/{user_id}/roles",
    response_model=UserRolesResponse
)
def assign_user_role(
    user_id: UUID,
    role_data: RoleAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("SUPER_ADMIN")
    )
):
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    role = db.scalar(
        select(Role).where(
            Role.name == role_data.role_name
        )
    )

    if role is None:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )

    if role not in user.roles:
        user.roles.append(role)
        db.commit()

    return UserRolesResponse(
        user_id=user.id,
        email=user.email,
        roles=[r.name for r in user.roles]
    )


# --------------------------------------------------
# REMOVE ROLE - SUPER ADMIN
# --------------------------------------------------

@router.delete(
    "/users/{user_id}/roles/{role_name}",
    response_model=UserRolesResponse
)
def remove_user_role(
    user_id: UUID,
    role_name: RoleName,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("SUPER_ADMIN")
    )
):
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    role = db.scalar(
        select(Role).where(Role.name == role_name)
    )

    if role is None or role not in user.roles:
        raise HTTPException(
            status_code=404,
            detail="User does not have this role"
        )

    if role_name == "SUPER_ADMIN":
        admin_count = db.scalar(
            select(func.count(User.id))
            .join(User.roles)
            .where(Role.name == "SUPER_ADMIN")
        )

        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove the last Super Admin"
            )

    user.roles.remove(role)
    db.commit()

    return UserRolesResponse(
        user_id=user.id,
        email=user.email,
        roles=[r.name for r in user.roles]
    )


# --------------------------------------------------
# ASSIGN DEPARTMENT - SUPER ADMIN
# --------------------------------------------------

@router.put("/users/{user_id}/department")
def assign_user_department(
    user_id: UUID,
    department_data: DepartmentAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("SUPER_ADMIN")
    )
):
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    department = db.get(
        Department,
        department_data.department_id
    )

    if department is None:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    user.department_id = department.id

    db.commit()
    db.refresh(user)

    return {
        "message": "Department assigned successfully",
        "user_id": str(user.id),
        "email": user.email,
        "department": department.name
    }


# --------------------------------------------------
# DEPARTMENT USER LIST
# SUPER ADMIN: ALL USERS
# DEPARTMENT ADMIN: OWN DEPARTMENT ONLY
# --------------------------------------------------

@router.get(
    "/department/users",
    response_model=list[UserRolesResponse]
)
def get_department_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("DEPARTMENT_ADMIN", "SUPER_ADMIN")
    )
):
    user_roles = {role.name for role in current_user.roles}

    query = select(User).order_by(User.email)

    if "SUPER_ADMIN" not in user_roles:

        if current_user.department_id is None:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to a department"
            )

        query = query.where(
            User.department_id == current_user.department_id
        )

    users = db.scalars(query).all()

    return [
        UserRolesResponse(
            user_id=user.id,
            email=user.email,
            roles=[r.name for r in user.roles]
        )
        for user in users
    ]
