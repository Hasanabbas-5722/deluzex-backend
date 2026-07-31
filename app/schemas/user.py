from pydantic import BaseModel, EmailStr
from typing import Optional, Any
from datetime import datetime

class UserRegister(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    phone: str
    accept_terms: bool

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserData(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

class StandardResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    data: Optional[UserData] = None
