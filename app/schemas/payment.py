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
    payment_method: Literal["upi", "card", "netbanking", "wallet", "cod"]
    razorpay_method: str = Field(..., description="Razorpay method key e.g. upi, card")
    idempotency_key: Optional[str] = None
    existing_order_id: Optional[str] = None
    upi_vpa: Optional[str] = None
    card_last4: Optional[str] = None
    bank_code: Optional[str] = None


class CreateOrderResponse(BaseModel):
    success: bool
    order_id: str
    razorpay_order_id: str
    amount: int
    currency: str
    key_id: str
    is_resumed: bool = False
    is_already_paid: bool = False


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
    idempotency_key: Optional[str] = None
    existing_order_id: Optional[str] = None


class CodOrderResponse(BaseModel):
    success: bool
    order_id: str
    message: str


class PaymentFailurePayload(BaseModel):
    order_id: str
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    status: str = "failed"
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    error_source: Optional[str] = None
    error_step: Optional[str] = None
    error_reason: Optional[str] = None


class PaymentFailureResponse(BaseModel):
    success: bool
    order_id: str
    message: str
    can_resume: bool = True


class CardPaymentInput(BaseModel):
    number: str
    name: str
    expiry: str
    cvv: str


class ServerPaymentRequest(BaseModel):
    email: EmailStr
    phone: str
    shipping_address: ShippingAddress
    items: List[OrderItem]
    subtotal: float
    gst: float
    delivery: float
    total: float
    payment_method: str = "upi"
    idempotency_key: Optional[str] = None
    existing_order_id: Optional[str] = None
    card: Optional[CardPaymentInput] = None
    upi_vpa: Optional[str] = None
    bank_code: Optional[str] = None


class ServerPaymentResponse(BaseModel):
    success: bool
    order_id: str
    payment_id: Optional[str] = None
    status: str
    message: str
    is_resumed: bool = False
    is_already_paid: bool = False
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    can_resume: bool = True


class InitiateUpiRequest(BaseModel):
    email: EmailStr
    phone: str
    shipping_address: ShippingAddress
    items: List[OrderItem]
    subtotal: float
    gst: float
    delivery: float
    total: float
    upi_vpa: str
    idempotency_key: Optional[str] = None
    existing_order_id: Optional[str] = None


class InitiateUpiResponse(BaseModel):
    success: bool
    order_id: str
    razorpay_order_id: Optional[str] = None
    upi_vpa: str
    amount: float
    status: str = "pending_approval"
    message: str
    payment_url: Optional[str] = None
    expires_in_seconds: int = 300


class PaymentStatusResponse(BaseModel):
    success: bool
    order_id: str
    status: str
    payment_id: Optional[str] = None
    message: str
    error_description: Optional[str] = None


class ConfirmUpiApprovalRequest(BaseModel):
    order_id: str
    simulated_status: Optional[str] = "approved"  # "approved" or "declined"

