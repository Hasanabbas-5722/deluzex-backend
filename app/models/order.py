from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.models.common import PyObjectId

OrderStatus = Literal[
    "pending",
    "paid",
    "failed",
    "cod",
    "processing",
    "shipped",
    "out_for_delivery",
    "delivered",
    "cancelled",
]
PaymentMethod = Literal["cod", "upi", "card", "netbanking", "wallet"]


class OrderItem(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int
    image: Optional[str] = None


class ShippingAddress(BaseModel):
    first_name: str
    last_name: str
    street: str
    city: str
    state: str
    pin_code: str


class Order(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: Optional[str] = None
    email: str
    phone: str
    shipping_address: ShippingAddress
    items: List[OrderItem]
    subtotal: float
    gst: float
    delivery: float
    total: float
    payment_method: PaymentMethod
    razorpay_method: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    status: OrderStatus = "pending"
    tracking_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True

