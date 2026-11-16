from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    file_type: str
    file_size: int
    status: str
    uploaded_by: UUID
    department_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)