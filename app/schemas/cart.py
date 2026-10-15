from pydantic import BaseModel
from typing import Optional, Any

class CartItemCreate(BaseModel):
    session_id: str
    product_id: str
    quantity: int = 1
    user_email: Optional[str] = None
    title: Optional[str] = None
    price: Optional[float] = None
    image: Optional[str] = None

class CartItemUpdate(BaseModel):
    quantity: int

class CartSyncRequest(BaseModel):
    session_id: str
    user_email: str

class CartItemResponse(BaseModel):
    id: str
    product_id: str
    title: str
    price: float
    image: str
    quantity: int
    session_id: Optional[str] = None
    user_email: Optional[str] = None

