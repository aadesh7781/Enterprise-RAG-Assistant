
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import User, Role
from app.schemas.auth import (
    UserRegister,
    UserResponse,
    UserLogin,
    TokenResponse
)
from app.security.password import hash_password, verify_password
from app.security.token import create_access_token
from app.security.dependencies import get_current_user


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"]
)


# -------------------------
# USER REGISTRATION
# -------------------------

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db)
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

    # Retrieve default EMPLOYEE role
    employee_role = db.scalar(
        select(Role).where(Role.name == "EMPLOYEE")
    )

    if employee_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default employee role is not configured"
        )

    # Create new user with default role
    new_user = User(
        email=email,
        full_name=user_data.full_name,
        password_hash=hash_password(user_data.password),
        roles=[employee_role]
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    return new_user


# -------------------------
# USER LOGIN
# -------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK
)
def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    email = str(user_data.email).lower()

    user = db.scalar(
        select(User).where(User.email == email)
    )

    if not user or not verify_password(
        user_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )


# -------------------------
# CURRENT AUTHENTICATED USER
# -------------------------

@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user
