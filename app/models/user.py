from beanie import Document
from pydantic import EmailStr, Field
from datetime import datetime
from typing import Optional

class User(Document):
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

    class Settings:
        name = "users"
