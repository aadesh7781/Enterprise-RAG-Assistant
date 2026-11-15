from fastapi import Depends, HTTPException, status

from app.models import User
from app.security.dependencies import get_current_user


def require_roles(*allowed_roles: str):

    def role_checker(
        current_user: User = Depends(get_current_user)
    ):
        user_roles = {role.name for role in current_user.roles}

        if not user_roles.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action"
            )

        return current_user

    return role_checker