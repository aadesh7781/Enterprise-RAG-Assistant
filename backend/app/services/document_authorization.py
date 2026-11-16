from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.models import User, Document, Department, Role


def get_authorized_document_ids(
    db: Session,
    current_user: User
) -> list[str]:

    user_roles = {
        role.name for role in current_user.roles
    }

    # Super Admin can access all documents.
    if "SUPER_ADMIN" in user_roles:

        document_ids = db.scalars(
            select(Document.id)
        ).all()

        return [str(document_id) for document_id in document_ids]

    access_conditions = []

    # Department-level grants.
    if current_user.department_id is not None:

        access_conditions.append(
            Document.department_grants.any(
                Department.id == current_user.department_id
            )
        )

    # Role-level grants.
    if user_roles:

        access_conditions.append(
            Document.role_grants.any(
                Role.name.in_(user_roles)
            )
        )

    # Individual-user grants.
    access_conditions.append(
        Document.user_grants.any(
            User.id == current_user.id
        )
    )

    statement = select(Document.id).where(
        or_(*access_conditions)
    )

    document_ids = db.scalars(statement).all()

    return [str(document_id) for document_id in document_ids]