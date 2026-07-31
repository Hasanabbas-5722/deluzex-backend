from beanie import Document, PydanticObjectId
from datetime import datetime
from pydantic import Field
from typing import Optional

class AuditLog(Document):
    user_id: Optional[PydanticObjectId] = None
    action: str
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "audit_logs"
