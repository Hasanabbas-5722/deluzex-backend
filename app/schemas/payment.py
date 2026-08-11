from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.order import OrderItem, ShippingAddress


class PaymentMethodInfo(BaseModel):
    id: str
    name: str
    description: str
    razorpay_method: str
    icon: str


class CreateOrderRequest(BaseModel):
    email: EmailStr
    phone: str
    shipping_address: ShippingAddress
    items: List[OrderItem]
    subtotal: float
    gst: float
    delivery: float
    total: float
    payment_method: Literal["upi", "card", "netbanking", "wallet"]
    razorpay_method: str = Field(..., description="Razorpay method key e.g. upi, card")


class CreateOrderResponse(BaseModel):
    success: bool
    order_id: str
    razorpay_order_id: str
    amount: int
    currency: str
    key_id: str


class VerifyPaymentRequest(BaseModel):
    order_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class VerifyPaymentResponse(BaseModel):
    success: bool
    order_id: str
    message: str


class CodOrderRequest(BaseModel):
    email: EmailStr
    phone: str
    shipping_address: ShippingAddress
    items: List[OrderItem]
    subtotal: float
    gst: float
    delivery: float
    total: float


class CodOrderResponse(BaseModel):
    success: bool
    order_id: str
    message: str
