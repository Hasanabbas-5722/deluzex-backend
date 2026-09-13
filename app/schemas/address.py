from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class AddressBase(BaseModel):
    user_email: str
    type: str = "Home"
    first_name: str
    last_name: Optional[str] = ""
    street: str
    city: str
    state: str
    pin_code: str
    phone: str
    is_default: bool = False

class AddressCreate(AddressBase):
    pass

class AddressUpdate(BaseModel):
    type: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    phone: Optional[str] = None
    is_default: Optional[bool] = None

class AddressResponse(AddressBase):
    id: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
