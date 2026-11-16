
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from datetime import datetime


# -----------------------------------------
# DOCUMENT PERMISSION ASSOCIATION TABLES
# -----------------------------------------

document_department_grants = Table(
    "document_department_grants",
    Base.metadata,
    Column(
        "document_id",
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "department_id",
        ForeignKey("departments.id", ondelete="CASCADE"),
        primary_key=True
    )
)


document_role_grants = Table(
    "document_role_grants",
    Base.metadata,
    Column(
        "document_id",
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "role_id",
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True
    )
)


document_user_grants = Table(
    "document_user_grants",
    Base.metadata,
    Column(
        "document_id",
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )
)


# -----------------------------------------
# DOCUMENT MODEL
# -----------------------------------------

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    stored_filename: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )

    storage_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False
    )

    uploaded_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Document relationships

    uploader = relationship(
        "User",
        foreign_keys=[uploaded_by]
    )

    department = relationship(
        "Department",
        foreign_keys=[department_id]
    )

    department_grants = relationship(
        "Department",
        secondary=document_department_grants
    )

    role_grants = relationship(
        "Role",
        secondary=document_role_grants
    )

    user_grants = relationship(
        "User",
        secondary=document_user_grants
    )
