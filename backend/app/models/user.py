from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id"),
        nullable=True
    )

    department: Mapped["Department | None"] = relationship(
        back_populates="users"
    )

    roles: Mapped[list["Role"]] = relationship(
    "Role",
    secondary="user_roles",
    back_populates="users"
)