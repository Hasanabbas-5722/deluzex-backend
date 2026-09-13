from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from app.models.common import PyObjectId

class Address(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
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
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True)
