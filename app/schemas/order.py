from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field

from app.models.order import OrderItem, ShippingAddress, OrderStatus, PaymentMethod


class OrderCreateRequest(BaseModel):
    user_id: Optional[str] = None
    email: EmailStr
    phone: str
    shipping_address: ShippingAddress
    items: List[OrderItem]
    subtotal: float
    gst: float
    delivery: float
    total: float
    payment_method: PaymentMethod
    notes: Optional[str] = None


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatus
    tracking_number: Optional[str] = None
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    id: str = Field(alias="_id")
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
    status: OrderStatus
    tracking_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True


class OrderListResponse(BaseModel):
    total_count: int
    orders: List[OrderResponse]


class OrderCancelResponse(BaseModel):
    success: bool
    order_id: str
    message: str
    status: str
