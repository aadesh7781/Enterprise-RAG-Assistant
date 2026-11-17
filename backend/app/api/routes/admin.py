
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models import User, Role, Department
from app.schemas.auth import UserResponse
from app.schemas.admin import (
    CreateUserRequest,
    RoleAssignmentRequest,
    DepartmentAssignmentRequest,
    UserRolesResponse,
    DepartmentResponse,
)
from app.security.permissions import require_roles
from app.security.password import hash_password


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
# LIST ALL USERS - SUPER ADMIN
# --------------------------------------------------

@router.get(
    "/users",
    response_model=list[UserResponse]
)
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("SUPER_ADMIN")
    )
):
    query = (
        select(User)
        .options(selectinload(User.roles))
        .order_by(User.email)
    )

    return db.scalars(query).all()


# --------------------------------------------------
# CREATE USER - SUPER ADMIN
# --------------------------------------------------

@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def create_user(
    user_data: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("SUPER_ADMIN")
    )
):
    email = str(user_data.email).lower()

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Department is mandatory for employees and department admins.
    if (
        user_data.role_name != "SUPER_ADMIN"
        and user_data.department_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A department is required for this role"
        )

    department = None

    if user_data.department_id is not None:
        department = db.get(
            Department,
            user_data.department_id
        )

        if department is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )

    role = db.scalar(
        select(Role).where(
            Role.name == user_data.role_name
        )
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    new_user = User(
        email=email,
        full_name=user_data.full_name.strip(),
        password_hash=hash_password(user_data.password),
        department_id=(
            department.id if department else None
        ),
        roles=[role]
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create user. Email may already exist."
        )

    return db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.id == new_user.id)
    )


# --------------------------------------------------
# LIST DEPARTMENTS - SUPER ADMIN
# --------------------------------------------------

@router.get(
    "/departments",
    response_model=list[DepartmentResponse]
)
def get_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("SUPER_ADMIN")
    )
):
    return db.scalars(
        select(Department).order_by(Department.name)
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
    user = db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.id == user_id)
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if (
        role_data.role_name != "SUPER_ADMIN"
        and user.department_id is None
    ):
        raise HTTPException(
            status_code=400,
            detail="Assign a department before assigning this role"
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
    role_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("SUPER_ADMIN")
    )
):
    allowed_roles = {
        "EMPLOYEE",
        "DEPARTMENT_ADMIN",
        "SUPER_ADMIN"
    }

    if role_name not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail="Invalid role name"
        )

    user = db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.id == user_id)
    )

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
# DEPARTMENT USERS
# SUPER ADMIN: ALL USERS
# DEPARTMENT ADMIN: OWN DEPARTMENT ONLY
# --------------------------------------------------

@router.get(
    "/department/users",
    response_model=list[UserResponse]
)
def get_department_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("DEPARTMENT_ADMIN", "SUPER_ADMIN")
    )
):
    user_roles = {
        role.name for role in current_user.roles
    }

    query = (
        select(User)
        .options(selectinload(User.roles))
        .order_by(User.email)
    )

    if "SUPER_ADMIN" not in user_roles:

        if current_user.department_id is None:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to a department"
            )

        query = query.where(
            User.department_id == current_user.department_id
        )

    return db.scalars(query).all()
