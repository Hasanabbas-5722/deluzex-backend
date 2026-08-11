from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.database import db
from app import models
from app.schemas.payment import (
    CodOrderRequest,
    CodOrderResponse,
    CreateOrderRequest,
    CreateOrderResponse,
    PaymentMethodInfo,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from app.services import razorpay as razorpay_service

router = APIRouter()

PAYMENT_METHODS: list[PaymentMethodInfo] = [
    PaymentMethodInfo(
        id="google_pay",
        name="Google Pay",
        description="Pay using Google Pay UPI",
        razorpay_method="upi",
        icon="google_pay",
    ),
    PaymentMethodInfo(
        id="phonepe",
        name="PhonePe",
        description="Pay using PhonePe UPI",
        razorpay_method="upi",
        icon="phonepe",
    ),
    PaymentMethodInfo(
        id="paytm",
        name="Paytm",
        description="Pay using Paytm UPI",
        razorpay_method="upi",
        icon="paytm",
    ),
    PaymentMethodInfo(
        id="bhim",
        name="BHIM UPI",
        description="Pay using BHIM UPI app",
        razorpay_method="upi",
        icon="bhim",
    ),
    PaymentMethodInfo(
        id="amazon_pay",
        name="Amazon Pay",
        description="Pay using Amazon Pay UPI",
        razorpay_method="upi",
        icon="amazon_pay",
    ),
    PaymentMethodInfo(
        id="upi_other",
        name="Other UPI Apps",
        description="Pay using any UPI app",
        razorpay_method="upi",
        icon="upi",
    ),
    PaymentMethodInfo(
        id="card",
        name="Credit / Debit Card",
        description="Visa, Mastercard, RuPay & more",
        razorpay_method="card",
        icon="card",
    ),
    PaymentMethodInfo(
        id="netbanking",
        name="Net Banking",
        description="All major Indian banks",
        razorpay_method="netbanking",
        icon="netbanking",
    ),
    PaymentMethodInfo(
        id="wallet",
        name="Wallets",
        description="Paytm, Mobikwik, Freecharge & more",
        razorpay_method="wallet",
        icon="wallet",
    ),
]


@router.get("/methods", response_model=list[PaymentMethodInfo])
def get_payment_methods():
    return PAYMENT_METHODS


@router.post("/create-order", response_model=CreateOrderResponse)
def create_order(payload: CreateOrderRequest):
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Payment gateway is not configured. Please contact support.",
        )

    amount_paise = round(payload.total * 100)
    if amount_paise < 100:
        raise HTTPException(status_code=400, detail="Order amount must be at least ₹1")

    receipt = razorpay_service.generate_receipt()

    try:
        razorpay_order = razorpay_service.create_razorpay_order(amount_paise, receipt)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail="Failed to create payment order"
        ) from exc

    db_order = models.Order(
        email=payload.email,
        phone=payload.phone,
        shipping_address=payload.shipping_address,
        items=payload.items,
        subtotal=payload.subtotal,
        gst=payload.gst,
        delivery=payload.delivery,
        total=payload.total,
        payment_method=payload.payment_method,
        razorpay_method=payload.razorpay_method,
        razorpay_order_id=razorpay_order["id"],
        status="pending",
    )

    result = db.orders.insert_one(
        db_order.model_dump(by_alias=True, exclude_none=True)
    )
    order_id = str(result.inserted_id)

    return CreateOrderResponse(
        success=True,
        order_id=order_id,
        razorpay_order_id=razorpay_order["id"],
        amount=amount_paise,
        currency=razorpay_order.get("currency", "INR"),
        key_id=settings.RAZORPAY_KEY_ID,
    )


@router.post("/verify", response_model=VerifyPaymentResponse)
def verify_payment(payload: VerifyPaymentRequest):
    from bson import ObjectId

    try:
        oid = ObjectId(payload.order_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid order ID") from exc

    is_valid = razorpay_service.verify_payment_signature(
        payload.razorpay_order_id,
        payload.razorpay_payment_id,
        payload.razorpay_signature,
    )

    if not is_valid:
        db.orders.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": "failed",
                    "razorpay_payment_id": payload.razorpay_payment_id,
                }
            },
        )
        raise HTTPException(status_code=400, detail="Payment verification failed")

    result = db.orders.update_one(
        {"_id": oid, "razorpay_order_id": payload.razorpay_order_id},
        {
            "$set": {
                "status": "paid",
                "razorpay_payment_id": payload.razorpay_payment_id,
            }
        },
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")

    return VerifyPaymentResponse(
        success=True,
        order_id=payload.order_id,
        message="Payment verified successfully",
    )


@router.post("/cod", response_model=CodOrderResponse)
def create_cod_order(payload: CodOrderRequest):
    db_order = models.Order(
        email=payload.email,
        phone=payload.phone,
        shipping_address=payload.shipping_address,
        items=payload.items,
        subtotal=payload.subtotal,
        gst=payload.gst,
        delivery=payload.delivery,
        total=payload.total,
        payment_method="cod",
        status="cod",
    )

    result = db.orders.insert_one(
        db_order.model_dump(by_alias=True, exclude_none=True)
    )

    return CodOrderResponse(
        success=True,
        order_id=str(result.inserted_id),
        message="Order placed successfully",
    )
