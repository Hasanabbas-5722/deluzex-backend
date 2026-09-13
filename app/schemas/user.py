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
    phone: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    is_verified: bool
    is_admin: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str

class StandardResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    data: Optional[UserData] = None
