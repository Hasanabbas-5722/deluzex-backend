from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from app.models.common import PyObjectId

class User(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    first_name: str
    last_name: str
    email: EmailStr
    hashed_password: str
    phone: Optional[str] = None
    accept_terms: bool
    is_active: bool = True
    is_verified: bool = False
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
