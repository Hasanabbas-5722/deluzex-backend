from pydantic import BaseModel
from typing import Optional

class CartItemCreate(BaseModel):
    session_id: str
    product_id: str
    quantity: int = 1
