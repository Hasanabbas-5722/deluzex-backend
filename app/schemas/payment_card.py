from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class PaymentCardBase(BaseModel):
    user_email: str
    card_holder: str
    card_number_masked: str
    card_last4: str
    card_type: str = "visa"
    expiry: str
    is_default: bool = False

class PaymentCardCreate(PaymentCardBase):
    pass

class PaymentCardUpdate(BaseModel):
    card_holder: Optional[str] = None
    card_number_masked: Optional[str] = None
    card_last4: Optional[str] = None
    card_type: Optional[str] = None
    expiry: Optional[str] = None
    is_default: Optional[bool] = None

class PaymentCardResponse(PaymentCardBase):
    id: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
