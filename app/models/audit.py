from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.models.common import PyObjectId

class AuditLog(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: Optional[PyObjectId] = None
    action: str
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
