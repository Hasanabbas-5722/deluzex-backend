from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.models.common import PyObjectId
from datetime import datetime

class ContactMessage(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
