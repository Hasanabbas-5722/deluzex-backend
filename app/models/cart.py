from pydantic import BaseModel, Field
from typing import Optional, Union, Any
from app.models.common import PyObjectId

class CartItem(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    session_id: str
    product_id: Union[PyObjectId, str]
    quantity: int = 1
    user_email: Optional[str] = None
    title: Optional[str] = None
    price: Optional[float] = 0.0
    image: Optional[str] = None

    class Config:
        populate_by_name = True

