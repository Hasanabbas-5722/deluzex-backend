from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from app.models.common import PyObjectId

class PaymentCard(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_email: str
    card_holder: str
    card_number_masked: str
    card_last4: str
    card_type: str = "visa"  # "visa", "mastercard", "rupay", "amex", "other"
    expiry: str  # "MM/YY"
    is_default: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True)
