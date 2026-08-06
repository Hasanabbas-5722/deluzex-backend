from pydantic import BaseModel, Field
from typing import Optional
from app.models.common import PyObjectId

class CartItem(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    session_id: str
    product_id: PyObjectId
    quantity: int = 1

    class Config:
        populate_by_name = True
