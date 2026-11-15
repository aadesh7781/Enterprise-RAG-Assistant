
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.auth import UserResponse
from app.database.session import get_db
from app.security.permissions import require_roles


router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Administration"]
)


# SUPER ADMIN TEST
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


# VIEW ALL USERS
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
    users = db.scalars(
        select(User).order_by(User.email)
    ).all()

    return users
