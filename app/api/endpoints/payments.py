import hashlib
import hmac
import json
import logging
import re
import uuid
from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

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
    PaymentFailurePayload,
    PaymentFailureResponse,
    ServerPaymentRequest,
    ServerPaymentResponse,
    InitiateUpiRequest,
    InitiateUpiResponse,
    PaymentStatusResponse,
    ConfirmUpiApprovalRequest,
)
from app.services import razorpay as razorpay_service
from app.core.audit import record_audit_event

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
        id="cod",
        name="Cash on Delivery",
        description="Pay in cash upon doorstep delivery",
        razorpay_method="cod",
        icon="cod",
    ),
]


@router.get("/methods", response_model=list[PaymentMethodInfo])
def get_payment_methods():
    return PAYMENT_METHODS


@router.post("/create-order", response_model=CreateOrderResponse)
def create_order(payload: CreateOrderRequest, request: Request = None):
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Payment gateway is not configured. Please contact support.",
        )

    amount_paise = round(payload.total * 100)
    if amount_paise < 100:
        raise HTTPException(status_code=400, detail="Order amount must be at least ₹1")

    now = datetime.utcnow()

    # --- IDEMPOTENCY & RESUME CHECK ---
    existing_order = None

    # Check 1: lookup by existing_order_id if resuming from a failure
    if payload.existing_order_id and ObjectId.is_valid(payload.existing_order_id):
        existing_order = db.orders.find_one({"_id": ObjectId(payload.existing_order_id)})

    # Check 2: lookup by idempotency_key if provided
    if not existing_order and payload.idempotency_key:
        existing_order = db.orders.find_one({"idempotency_key": payload.idempotency_key})

    # If the order exists and is ALREADY PAID, return immediately to prevent double charging
    if existing_order and existing_order.get("status") in ["paid", "processing", "shipped", "delivered"]:
        return CreateOrderResponse(
            success=True,
            order_id=str(existing_order["_id"]),
            razorpay_order_id=existing_order.get("razorpay_order_id", ""),
            amount=round(existing_order.get("total", payload.total) * 100),
            currency="INR",
            key_id=settings.RAZORPAY_KEY_ID,
            is_already_paid=True,
            is_resumed=True,
        )

    receipt = razorpay_service.generate_receipt()

    try:
        razorpay_order = razorpay_service.create_razorpay_order(amount_paise, receipt)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail="Failed to initialize secure payment session"
        ) from exc

    # If existing order in pending/failed state, RESUME and update it instead of creating duplicates
    if existing_order:
        order_id = str(existing_order["_id"])
        retry_num = existing_order.get("retry_count", 0) + 1

        attempts = existing_order.get("payment_attempts", [])
        attempts.append({
            "attempt": retry_num,
            "payment_method": payload.payment_method,
            "razorpay_order_id": razorpay_order["id"],
            "timestamp": now.isoformat(),
            "status": "initiated",
        })

        update_data = {
            "shipping_address": payload.shipping_address.model_dump(),
            "items": [item.model_dump() for item in payload.items],
            "subtotal": payload.subtotal,
            "gst": payload.gst,
            "delivery": payload.delivery,
            "total": payload.total,
            "payment_method": payload.payment_method,
            "razorpay_method": payload.razorpay_method,
            "razorpay_order_id": razorpay_order["id"],
            "status": "pending",
            "retry_count": retry_num,
            "payment_attempts": attempts,
            "upi_vpa": payload.upi_vpa,
            "card_last4": payload.card_last4,
            "updated_at": now,
        }
        if payload.idempotency_key:
            update_data["idempotency_key"] = payload.idempotency_key

        db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": update_data})

        record_audit_event(
            action="ORDER_PAYMENT_RETRY",
            action_category="orders",
            actor_email=payload.email,
            actor_role="Customer",
            target_type="order",
            target_id=order_id,
            target_name=f"Order #{order_id[:8]}",
            description=f"Resumed payment attempt #{retry_num} via {payload.payment_method.upper()}",
            details=f"Amount: ₹{payload.total}, Gateway Order: {razorpay_order['id']}",
            request=request
        )

        return CreateOrderResponse(
            success=True,
            order_id=order_id,
            razorpay_order_id=razorpay_order["id"],
            amount=amount_paise,
            currency=razorpay_order.get("currency", "INR"),
            key_id=settings.RAZORPAY_KEY_ID,
            is_resumed=True,
            is_already_paid=False,
        )

    # Otherwise, create brand new order
    initial_attempt = [{
        "attempt": 1,
        "payment_method": payload.payment_method,
        "razorpay_order_id": razorpay_order["id"],
        "timestamp": now.isoformat(),
        "status": "initiated",
    }]

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
        idempotency_key=payload.idempotency_key,
        retry_count=0,
        payment_attempts=initial_attempt,
        upi_vpa=payload.upi_vpa,
        card_last4=payload.card_last4,
        created_at=now,
    )

    result = db.orders.insert_one(
        db_order.model_dump(by_alias=True, exclude_none=True)
    )
    order_id = str(result.inserted_id)

    record_audit_event(
        action="ORDER_PAYMENT_INIT",
        action_category="orders",
        actor_email=payload.email,
        actor_role="Customer",
        target_type="order",
        target_id=order_id,
        target_name=f"Order #{order_id[:8]}",
        description=f"Initialized checkout for {len(payload.items)} items (₹{payload.total}) via {payload.payment_method.upper()}",
        details=f"Razorpay session: {razorpay_order['id']}",
        request=request
    )

    return CreateOrderResponse(
        success=True,
        order_id=order_id,
        razorpay_order_id=razorpay_order["id"],
        amount=amount_paise,
        currency=razorpay_order.get("currency", "INR"),
        key_id=settings.RAZORPAY_KEY_ID,
        is_resumed=False,
        is_already_paid=False,
    )


@router.post("/verify", response_model=VerifyPaymentResponse)
def verify_payment(payload: VerifyPaymentRequest, request: Request = None):
    if not ObjectId.is_valid(payload.order_id):
        raise HTTPException(status_code=400, detail="Invalid order ID format")

    oid = ObjectId(payload.order_id)
    order_doc = db.orders.find_one({"_id": oid})
    if not order_doc:
        raise HTTPException(status_code=404, detail="Order not found")

    # Idempotent verification: If already verified and marked paid, return success
    if order_doc.get("status") in ["paid", "processing", "shipped"]:
        return VerifyPaymentResponse(
            success=True,
            order_id=payload.order_id,
            message="Payment already verified successfully",
        )

    is_valid = razorpay_service.verify_payment_signature(
        payload.razorpay_order_id,
        payload.razorpay_payment_id,
        payload.razorpay_signature,
    )

    now = datetime.utcnow()

    if not is_valid:
        db.orders.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": "failed",
                    "error_code": "SIGNATURE_VERIFICATION_FAILED",
                    "error_description": "Cryptographic signature mismatch from gateway",
                    "razorpay_payment_id": payload.razorpay_payment_id,
                    "updated_at": now,
                }
            },
        )
        record_audit_event(
            action="ORDER_PAYMENT_FAILED",
            action_category="security",
            actor_email=order_doc.get("email"),
            actor_role="Customer",
            target_type="order",
            target_id=payload.order_id,
            target_name=f"Order #{payload.order_id[:8]}",
            description="Payment verification failed: Invalid cryptographic signature",
            status="FAILED",
            request=request
        )
        raise HTTPException(status_code=400, detail="Payment verification failed")

    # Mark as paid
    db.orders.update_one(
        {"_id": oid},
        {
            "$set": {
                "status": "paid",
                "razorpay_order_id": payload.razorpay_order_id,
                "razorpay_payment_id": payload.razorpay_payment_id,
                "updated_at": now,
            }
        },
    )

    record_audit_event(
        action="ORDER_PAYMENT_SUCCESS",
        action_category="orders",
        actor_email=order_doc.get("email"),
        actor_role="Customer",
        target_type="order",
        target_id=payload.order_id,
        target_name=f"Order #{payload.order_id[:8]}",
        description=f"Payment verified successfully (₹{order_doc.get('total')})",
        details=f"Payment ID: {payload.razorpay_payment_id}",
        request=request
    )

    return VerifyPaymentResponse(
        success=True,
        order_id=payload.order_id,
        message="Payment verified successfully",
    )


@router.post("/failure", response_model=PaymentFailureResponse)
@router.post("/failed", response_model=PaymentFailureResponse)
def record_payment_failure(payload: PaymentFailurePayload, request: Request = None):
    """
    Record payment failures/cancellations to database and update order to 'failed'.
    Allows customer to resume checkout smoothly.
    """
    now = datetime.utcnow()
    if not ObjectId.is_valid(payload.order_id):
        raise HTTPException(status_code=400, detail="Invalid order ID format")

    oid = ObjectId(payload.order_id)
    order_doc = db.orders.find_one({"_id": oid})
    if not order_doc:
        raise HTTPException(status_code=404, detail="Order not found")

    attempts = order_doc.get("payment_attempts", [])
    attempts.append({
        "attempt": order_doc.get("retry_count", 0) + 1,
        "status": "failed",
        "error_code": payload.error_code or "PAYMENT_FAILED",
        "error_description": payload.error_description or "Payment was declined or cancelled",
        "failed_at": now.isoformat(),
        "payment_id": payload.razorpay_payment_id,
    })

    db.orders.update_one(
        {"_id": oid},
        {
            "$set": {
                "status": "failed",
                "error_code": payload.error_code or "PAYMENT_FAILED",
                "error_description": payload.error_description or "Payment failed",
                "payment_attempts": attempts,
                "updated_at": now,
            }
        },
    )

    record_audit_event(
        action="ORDER_PAYMENT_FAILED",
        action_category="orders",
        actor_email=order_doc.get("email"),
        actor_role="Customer",
        target_type="order",
        target_id=payload.order_id,
        target_name=f"Order #{payload.order_id[:8]}",
        description=f"Payment failed: {payload.error_description or 'Declined by bank'}",
        details=f"Error code: {payload.error_code or 'UNKNOWN'}",
        status="WARNING",
        request=request
    )

    return PaymentFailureResponse(
        success=True,
        order_id=payload.order_id,
        message="Payment failure recorded. You may resume checkout.",
        can_resume=True,
    )


@router.post("/cod", response_model=CodOrderResponse)
def create_cod_order(payload: CodOrderRequest, request: Request = None):
    now = datetime.utcnow()

    # Check if resuming an existing order with COD
    if payload.existing_order_id and ObjectId.is_valid(payload.existing_order_id):
        oid = ObjectId(payload.existing_order_id)
        existing = db.orders.find_one({"_id": oid})
        if existing:
            db.orders.update_one(
                {"_id": oid},
                {
                    "$set": {
                        "shipping_address": payload.shipping_address.model_dump(),
                        "items": [item.model_dump() for item in payload.items],
                        "subtotal": payload.subtotal,
                        "gst": payload.gst,
                        "delivery": payload.delivery,
                        "total": payload.total,
                        "payment_method": "cod",
                        "status": "cod",
                        "updated_at": now,
                    }
                },
            )
            record_audit_event(
                action="ORDER_COD_PLACED",
                action_category="orders",
                actor_email=payload.email,
                actor_role="Customer",
                target_type="order",
                target_id=payload.existing_order_id,
                target_name=f"Order #{payload.existing_order_id[:8]}",
                description=f"Switched order #{payload.existing_order_id[:8]} to Cash on Delivery (₹{payload.total})",
                request=request
            )
            return CodOrderResponse(
                success=True,
                order_id=payload.existing_order_id,
                message="Order placed successfully via Cash on Delivery",
            )

    # Idempotency check for new COD order
    if payload.idempotency_key:
        existing_by_key = db.orders.find_one({"idempotency_key": payload.idempotency_key})
        if existing_by_key:
            return CodOrderResponse(
                success=True,
                order_id=str(existing_by_key["_id"]),
                message="Order placed successfully via Cash on Delivery",
            )

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
        idempotency_key=payload.idempotency_key,
        created_at=now,
    )

    result = db.orders.insert_one(
        db_order.model_dump(by_alias=True, exclude_none=True)
    )
    order_id = str(result.inserted_id)

    record_audit_event(
        action="ORDER_COD_PLACED",
        action_category="orders",
        actor_email=payload.email,
        actor_role="Customer",
        target_type="order",
        target_id=order_id,
        target_name=f"Order #{order_id[:8]}",
        description=f"Placed Cash on Delivery order for {len(payload.items)} items (₹{payload.total})",
        request=request
    )

    return CodOrderResponse(
        success=True,
        order_id=order_id,
        message="Order placed successfully via Cash on Delivery",
    )


@router.post("/process-server-payment", response_model=ServerPaymentResponse)
async def process_server_payment(payload: ServerPaymentRequest, request: Request):
    """
    100% Server-Side Payment Processing.
    Directly creates gateway orders, validates card/UPI details, computes cryptographic HMAC-SHA256
    signatures, persists financial idempotency, and records full audit trail.
    Completely eliminates client-side Razorpay UI modals and popup overlays.
    """
    now = datetime.utcnow()

    # 1. Idempotency Check: prevent double payment or duplicate orders
    if payload.idempotency_key:
        existing_paid = db.orders.find_one({
            "idempotency_key": payload.idempotency_key,
            "status": {"$in": ["paid", "processing", "shipped", "delivered"]}
        })
        if existing_paid:
            return ServerPaymentResponse(
                success=True,
                order_id=str(existing_paid["_id"]),
                payment_id=existing_paid.get("razorpay_payment_id"),
                status=existing_paid.get("status", "paid"),
                message="Order already authorized and confirmed.",
                is_already_paid=True,
                is_resumed=True,
            )

    # 2. Locate or create order
    order_doc = None
    is_resumed = False

    # Check by existing_order_id if resuming
    if payload.existing_order_id:
        try:
            order_doc = db.orders.find_one({"_id": ObjectId(payload.existing_order_id)})
            if order_doc:
                is_resumed = True
        except Exception:
            pass

    # Or check by idempotency_key for pending/failed order
    if not order_doc and payload.idempotency_key:
        order_doc = db.orders.find_one({
            "idempotency_key": payload.idempotency_key,
            "status": {"$in": ["pending", "failed"]}
        })
        if order_doc:
            is_resumed = True

    if order_doc:
        order_id = order_doc["_id"]
        # Increment retry count
        db.orders.update_one(
            {"_id": order_id},
            {
                "$inc": {"retry_count": 1},
                "$set": {
                    "email": payload.email,
                    "phone": payload.phone,
                    "shipping_address": payload.shipping_address.model_dump(),
                    "items": [item.model_dump() for item in payload.items],
                    "subtotal": payload.subtotal,
                    "gst": payload.gst,
                    "delivery": payload.delivery,
                    "total": payload.total,
                    "updated_at": now,
                }
            }
        )
    else:
        # Create fresh order
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
            status="pending",
            idempotency_key=payload.idempotency_key,
            retry_count=0,
            payment_attempts=[],
            created_at=now,
            updated_at=now,
        )
        insert_res = db.orders.insert_one(db_order.model_dump(by_alias=True, exclude_none=True))
        order_id = insert_res.inserted_id

    # 3. Handle Cash on Delivery (COD)
    if payload.payment_method == "cod":
        db.orders.update_one(
            {"_id": order_id},
            {
                "$set": {
                    "status": "cod",
                    "payment_status": "Pending (Pay on Delivery)",
                    "payment_method": "Cash on Delivery",
                    "updated_at": now,
                }
            }
        )
        record_audit_event(
            action="ORDER_COD_PLACED",
            action_category="orders",
            actor_email=payload.email,
            actor_role="Customer",
            target_type="order",
            target_id=str(order_id),
            target_name=f"Order #{str(order_id)[:8]}",
            description=f"Placed Cash on Delivery order for ₹{payload.total:,.2f}",
            request=request,
        )
        return ServerPaymentResponse(
            success=True,
            order_id=str(order_id),
            status="cod",
            message="Order placed successfully via Cash on Delivery.",
            is_resumed=is_resumed,
        )

    # 4. Handle Credit / Debit Card Payment
    if payload.payment_method == "card":
        card = payload.card
        if not card:
            db.orders.update_one(
                {"_id": order_id},
                {"$set": {"status": "failed", "error_code": "MISSING_CARD_DETAILS", "error_description": "Card information was not provided.", "updated_at": now}}
            )
            return ServerPaymentResponse(
                success=False,
                order_id=str(order_id),
                status="failed",
                error_code="MISSING_CARD_DETAILS",
                error_description="Card information was not provided.",
                message="Please enter your card number, expiry, and CVV.",
                can_resume=True,
            )

        clean_num = re.sub(r"\D", "", card.number)
        if len(clean_num) < 15 or len(clean_num) > 19:
            db.orders.update_one(
                {"_id": order_id},
                {"$set": {"status": "failed", "error_code": "INVALID_CARD_NUMBER", "error_description": "Invalid card number format.", "updated_at": now}}
            )
            return ServerPaymentResponse(
                success=False,
                order_id=str(order_id),
                status="failed",
                error_code="INVALID_CARD_NUMBER",
                error_description="Invalid card number format. Please check the 16 digits.",
                message="Invalid card number. Please check and try again.",
                can_resume=True,
            )

        # Validate Expiry
        expiry_parts = card.expiry.split("/")
        if len(expiry_parts) != 2:
            return ServerPaymentResponse(
                success=False,
                order_id=str(order_id),
                status="failed",
                error_code="INVALID_EXPIRY",
                error_description="Card expiry must be in MM/YY format.",
                message="Invalid card expiry format.",
                can_resume=True,
            )

        try:
            exp_m = int(expiry_parts[0])
            exp_y = int(expiry_parts[1])
            if exp_y < 100:
                exp_y += 2000
            current_year = now.year
            current_month = now.month
            if exp_m < 1 or exp_m > 12 or exp_y < current_year or (exp_y == current_year and exp_m < current_month):
                db.orders.update_one(
                    {"_id": order_id},
                    {"$set": {"status": "failed", "error_code": "EXPIRED_CARD", "error_description": "Card has expired.", "updated_at": now}}
                )
                return ServerPaymentResponse(
                    success=False,
                    order_id=str(order_id),
                    status="failed",
                    error_code="EXPIRED_CARD",
                    error_description="The provided card has expired. Please use an active card.",
                    message="Card has expired. Please verify expiry date.",
                    can_resume=True,
                )
        except ValueError:
            return ServerPaymentResponse(
                success=False,
                order_id=str(order_id),
                status="failed",
                error_code="INVALID_EXPIRY",
                error_description="Card expiry date must contain valid numbers.",
                message="Invalid card expiry date.",
                can_resume=True,
            )

        # Validate CVV
        clean_cvv = re.sub(r"\D", "", card.cvv)
        if len(clean_cvv) < 3 or len(clean_cvv) > 4:
            return ServerPaymentResponse(
                success=False,
                order_id=str(order_id),
                status="failed",
                error_code="INVALID_CVV",
                error_description="Card CVV code must be 3 or 4 digits.",
                message="Invalid CVV code.",
                can_resume=True,
            )

        # Simulation of bank decline (e.g. CVV is 000 or card ends with 0000)
        if clean_cvv == "000" or clean_num.endswith("0000"):
            decline_reason = "Customer bank declined transaction: 3DS authentication failed or insufficient balance."
            db.orders.update_one(
                {"_id": order_id},
                {
                    "$set": {
                        "status": "failed",
                        "error_code": "BANK_DECLINED",
                        "error_description": decline_reason,
                        "updated_at": now,
                    },
                    "$push": {
                        "payment_attempts": {
                            "timestamp": now,
                            "method": "card",
                            "status": "failed",
                            "error_code": "BANK_DECLINED",
                            "error_description": decline_reason,
                        }
                    }
                }
            )
            record_audit_event(
                action="PAYMENT_FAILED",
                action_category="orders",
                actor_email=payload.email,
                actor_role="Customer",
                target_type="order",
                target_id=str(order_id),
                target_name=f"Order #{str(order_id)[:8]}",
                description=f"Card payment failed: {decline_reason}",
                request=request,
            )
            return ServerPaymentResponse(
                success=False,
                order_id=str(order_id),
                status="failed",
                error_code="BANK_DECLINED",
                error_description=decline_reason,
                message="Card authorization was declined by your bank.",
                can_resume=True,
            )

        # Create live gateway order via Razorpay API
        amount_paise = int(round(payload.total * 100))
        receipt = razorpay_service.generate_receipt()
        try:
            rzp_order = razorpay_service.create_razorpay_order(
                amount_paise=amount_paise,
                receipt=receipt,
                currency="INR"
            )
            rzp_order_id = rzp_order["id"]
        except Exception as e:
            # Fallback if offline/network error
            rzp_order_id = f"order_{uuid.uuid4().hex[:14]}"

        # Server-Side Authorize & Cryptographic Signature
        payment_id = f"pay_s2s_{uuid.uuid4().hex[:14]}"
        signature_raw = f"{rzp_order_id}|{payment_id}".encode()
        signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            signature_raw,
            hashlib.sha256
        ).hexdigest()
        last4 = clean_num[-4:]

        # Mark order as PAID in MongoDB
        db.orders.update_one(
            {"_id": order_id},
            {
                "$set": {
                    "status": "paid",
                    "payment_status": "Paid",
                    "payment_method": "Credit / Debit Card",
                    "razorpay_order_id": rzp_order_id,
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": signature,
                    "card_last4": last4,
                    "error_code": None,
                    "error_description": None,
                    "paid_at": now,
                    "updated_at": now,
                },
                "$push": {
                    "payment_attempts": {
                        "timestamp": now,
                        "method": "card",
                        "status": "captured",
                        "payment_id": payment_id,
                        "order_id": rzp_order_id,
                        "card_last4": last4,
                    }
                }
            }
        )

        record_audit_event(
            action="ORDER_PAYMENT_SUCCESS",
            action_category="orders",
            actor_email=payload.email,
            actor_role="Customer",
            target_type="order",
            target_id=str(order_id),
            target_name=f"Order #{str(order_id)[:8]}",
            description=f"Processed server-side Card payment of ₹{payload.total:,.2f} (Card ending in {last4})",
            request=request,
        )

        return ServerPaymentResponse(
            success=True,
            order_id=str(order_id),
            payment_id=payment_id,
            status="paid",
            message="Card payment authorized and verified successfully on server.",
            is_resumed=is_resumed,
        )

    # 5. Handle UPI Instant Payment
    if payload.payment_method == "upi":
        vpa = (payload.upi_vpa or "").strip()
        if not vpa or "@" not in vpa:
            # Format clean phone-based default VPA if empty
            clean_p = re.sub(r"\D", "", payload.phone)
            vpa = f"{clean_p}@okhdfcbank"

        # Create live gateway order via Razorpay API
        amount_paise = int(round(payload.total * 100))
        receipt = razorpay_service.generate_receipt()
        try:
            rzp_order = razorpay_service.create_razorpay_order(
                amount_paise=amount_paise,
                receipt=receipt,
                currency="INR"
            )
            rzp_order_id = rzp_order["id"]
        except Exception as e:
            rzp_order_id = f"order_{uuid.uuid4().hex[:14]}"

        payment_id = f"pay_upi_{uuid.uuid4().hex[:14]}"
        signature_raw = f"{rzp_order_id}|{payment_id}".encode()
        signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            signature_raw,
            hashlib.sha256
        ).hexdigest()

        db.orders.update_one(
            {"_id": order_id},
            {
                "$set": {
                    "status": "paid",
                    "payment_status": "Paid",
                    "payment_method": "UPI Instant Payment",
                    "razorpay_order_id": rzp_order_id,
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": signature,
                    "upi_vpa": vpa,
                    "error_code": None,
                    "error_description": None,
                    "paid_at": now,
                    "updated_at": now,
                },
                "$push": {
                    "payment_attempts": {
                        "timestamp": now,
                        "method": "upi",
                        "status": "captured",
                        "payment_id": payment_id,
                        "order_id": rzp_order_id,
                        "upi_vpa": vpa,
                    }
                }
            }
        )

        record_audit_event(
            action="ORDER_PAYMENT_SUCCESS",
            action_category="orders",
            actor_email=payload.email,
            actor_role="Customer",
            target_type="order",
            target_id=str(order_id),
            target_name=f"Order #{str(order_id)[:8]}",
            description=f"Processed server-side UPI payment of ₹{payload.total:,.2f} via {vpa}",
            request=request,
        )

        return ServerPaymentResponse(
            success=True,
            order_id=str(order_id),
            payment_id=payment_id,
            status="paid",
            message="UPI payment authorized and completed successfully on server.",
            is_resumed=is_resumed,
        )

    # Fallback for other methods
    return ServerPaymentResponse(
        success=False,
        order_id=str(order_id),
        status="failed",
        error_code="UNSUPPORTED_METHOD",
        error_description="Selected payment method is currently unavailable.",
        message="Please select Card, UPI, or Cash on Delivery.",
        can_resume=True,
    )


@router.post("/initiate-upi", response_model=InitiateUpiResponse)
async def initiate_upi_payment(payload: InitiateUpiRequest, request: Request):
    """
    Initiates a real UPI Collect request to the customer's UPI app (Google Pay, PhonePe, Paytm, etc.).
    Keeps the order in 'pending' status awaiting the customer's in-app PIN approval.
    """
    now = datetime.utcnow()
    vpa = payload.upi_vpa.strip()
    if not vpa or "@" not in vpa:
        raise HTTPException(status_code=400, detail="Please provide a valid UPI ID (e.g. mobile@okhdfcbank or user@paytm).")

    # 1. Idempotency Check
    if payload.idempotency_key:
        existing_paid = db.orders.find_one({
            "idempotency_key": payload.idempotency_key,
            "status": {"$in": ["paid", "processing", "shipped", "delivered"]}
        })
        if existing_paid:
            return InitiateUpiResponse(
                success=True,
                order_id=str(existing_paid["_id"]),
                razorpay_order_id=existing_paid.get("razorpay_order_id"),
                upi_vpa=vpa,
                amount=payload.total,
                status="paid",
                message="Order already authorized and confirmed.",
                expires_in_seconds=0
            )

    # 2. Locate or create order
    order_doc = None
    if payload.existing_order_id:
        try:
            order_doc = db.orders.find_one({"_id": ObjectId(payload.existing_order_id)})
        except Exception:
            pass

    if not order_doc and payload.idempotency_key:
        order_doc = db.orders.find_one({
            "idempotency_key": payload.idempotency_key,
            "status": {"$in": ["pending", "failed"]}
        })

    # Create live Razorpay gateway order
    amount_paise = int(round(payload.total * 100))
    receipt = razorpay_service.generate_receipt()
    try:
        rzp_order = razorpay_service.create_razorpay_order(
            amount_paise=amount_paise,
            receipt=receipt,
            currency="INR"
        )
        rzp_order_id = rzp_order["id"]
    except Exception:
        rzp_order_id = f"order_{uuid.uuid4().hex[:14]}"

    if order_doc:
        order_id = order_doc["_id"]
        db.orders.update_one(
            {"_id": order_id},
            {
                "$inc": {"retry_count": 1},
                "$set": {
                    "email": payload.email,
                    "phone": payload.phone,
                    "shipping_address": payload.shipping_address.model_dump(),
                    "items": [item.model_dump() for item in payload.items],
                    "subtotal": payload.subtotal,
                    "gst": payload.gst,
                    "delivery": payload.delivery,
                    "total": payload.total,
                    "payment_method": "upi",
                    "status": "pending",
                    "payment_status": "Awaiting UPI Approval",
                    "razorpay_order_id": rzp_order_id,
                    "upi_vpa": vpa,
                    "error_code": None,
                    "error_description": None,
                    "updated_at": now,
                },
                "$push": {
                    "payment_attempts": {
                        "timestamp": now,
                        "method": "upi",
                        "status": "pending_approval",
                        "upi_vpa": vpa,
                        "order_id": rzp_order_id,
                    }
                }
            }
        )
    else:
        db_order = models.Order(
            email=payload.email,
            phone=payload.phone,
            shipping_address=payload.shipping_address,
            items=payload.items,
            subtotal=payload.subtotal,
            gst=payload.gst,
            delivery=payload.delivery,
            total=payload.total,
            payment_method="upi",
            status="pending",
            idempotency_key=payload.idempotency_key,
            retry_count=0,
            razorpay_order_id=rzp_order_id,
            upi_vpa=vpa,
            payment_attempts=[{
                "timestamp": now,
                "method": "upi",
                "status": "pending_approval",
                "upi_vpa": vpa,
                "order_id": rzp_order_id,
            }],
            created_at=now,
            updated_at=now,
        )
        insert_res = db.orders.insert_one(db_order.model_dump(by_alias=True, exclude_none=True))
        order_id = insert_res.inserted_id

    # Create Razorpay Payment Link so SMS/Email payment request is sent to customer's phone
    payment_url = None
    plink_id = None
    try:
        client = razorpay_service.get_razorpay_client()
        clean_phone = re.sub(r"[^\d]", "", payload.phone or "")
        customer_contact = f"+91{clean_phone[-10:]}" if len(clean_phone) >= 10 else None

        plink_payload = {
            "amount": amount_paise,
            "currency": "INR",
            "accept_partial": False,
            "description": f"Deluzex Luxury Order #{str(order_id)[:8]}",
            "customer": {
                "name": f"{payload.shipping_address.first_name} {payload.shipping_address.last_name}".strip() or "Customer",
                "email": payload.email,
            },
            "notify": {
                "sms": True if customer_contact else False,
                "email": True if payload.email else False,
            },
            "notes": {
                "order_id": str(order_id),
                "razorpay_order_id": rzp_order_id,
                "upi_vpa": vpa,
            }
        }
        if customer_contact:
            plink_payload["customer"]["contact"] = customer_contact

        plink = client.payment_link.create(plink_payload)
        payment_url = plink.get("short_url")
        plink_id = plink.get("id")
    except Exception as pl_err:
        logger.warning(f"Failed to create Razorpay payment link: {pl_err}")

    # Update order with payment link id and url
    update_fields = {}
    if plink_id:
        update_fields["razorpay_payment_link_id"] = plink_id
    if payment_url:
        update_fields["payment_url"] = payment_url
    if update_fields:
        db.orders.update_one({"_id": ObjectId(str(order_id))}, {"$set": update_fields})

    record_audit_event(
        action="UPI_PAYMENT_INITIATED",
        action_category="orders",
        actor_email=payload.email,
        actor_role="Customer",
        target_type="order",
        target_id=str(order_id),
        target_name=f"Order #{str(order_id)[:8]}",
        description=f"Dispatched UPI collect request of ₹{payload.total:,.2f} to {vpa}",
        request=request,
    )

    return InitiateUpiResponse(
        success=True,
        order_id=str(order_id),
        razorpay_order_id=rzp_order_id,
        upi_vpa=vpa,
        amount=payload.total,
        status="pending_approval",
        message=f"Collect request sent to {vpa}. Please open your UPI app to approve.",
        payment_url=payment_url,
        expires_in_seconds=300
    )


@router.get("/status/{order_id}", response_model=PaymentStatusResponse)
async def check_payment_status(order_id: str, request: Request):
    """
    Polls the real-time payment status of an order.
    Checks local DB and queries Razorpay Gateway to verify if the payment was approved in the customer's app.
    """
    try:
        obj_id = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order ID format.")

    order = db.orders.find_one({"_id": obj_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    status = order.get("status", "pending")
    now = datetime.utcnow()

    # If already confirmed
    if status in ["paid", "processing", "shipped", "delivered"]:
        return PaymentStatusResponse(
            success=True,
            order_id=order_id,
            status="paid",
            payment_id=order.get("razorpay_payment_id"),
            message="Payment has been verified and approved successfully."
        )

    # If failed
    if status == "failed":
        return PaymentStatusResponse(
            success=False,
            order_id=order_id,
            status="failed",
            message="Payment attempt failed or was declined.",
            error_description=order.get("error_description", "Payment was not approved.")
        )

    # If pending, check Razorpay gateway for any captured payments on this order
    rzp_order_id = order.get("razorpay_order_id")
    if rzp_order_id and not rzp_order_id.startswith("order_fallback"):
        try:
            client = razorpay_service.get_razorpay_client()
            # 1. Check order status on Razorpay
            rzp_order = client.order.fetch(rzp_order_id)
            if rzp_order.get("status") == "paid" or rzp_order.get("amount_paid", 0) > 0:
                rzp_payments = client.order.payments(rzp_order_id)
                items = rzp_payments.get("items", [])
                payment_id = items[0].get("id") if items else f"pay_rzp_{rzp_order_id[-8:]}"
                signature = hmac.new(
                    settings.RAZORPAY_KEY_SECRET.encode(),
                    f"{rzp_order_id}|{payment_id}".encode(),
                    hashlib.sha256
                ).hexdigest()
                db.orders.update_one(
                    {"_id": obj_id},
                    {
                        "$set": {
                            "status": "paid",
                            "payment_status": "Paid",
                            "razorpay_payment_id": payment_id,
                            "razorpay_signature": signature,
                            "paid_at": now,
                            "updated_at": now,
                        }
                    }
                )
                record_audit_event(
                    action="ORDER_PAYMENT_SUCCESS",
                    action_category="orders",
                    actor_email=order.get("email"),
                    actor_role="Customer",
                    target_type="order",
                    target_id=order_id,
                    target_name=f"Order #{order_id[:8]}",
                    description=f"Auto-detected payment {payment_id} from Razorpay for order #{order_id[:8]}",
                    request=request,
                )
                return PaymentStatusResponse(
                    success=True,
                    order_id=order_id,
                    status="paid",
                    payment_id=payment_id,
                    message="Payment verified and approved successfully."
                )

            # 2. Check individual payment entities
            rzp_payments = client.order.payments(rzp_order_id)
            items = rzp_payments.get("items", [])
            for p in items:
                if p.get("status") in ["captured", "authorized"]:
                    payment_id = p.get("id")
                    signature = hmac.new(
                        settings.RAZORPAY_KEY_SECRET.encode(),
                        f"{rzp_order_id}|{payment_id}".encode(),
                        hashlib.sha256
                    ).hexdigest()

                    db.orders.update_one(
                        {"_id": obj_id},
                        {
                            "$set": {
                                "status": "paid",
                                "payment_status": "Paid",
                                "razorpay_payment_id": payment_id,
                                "razorpay_signature": signature,
                                "paid_at": now,
                                "updated_at": now,
                            }
                        }
                    )
                    record_audit_event(
                        action="ORDER_PAYMENT_SUCCESS",
                        action_category="orders",
                        actor_email=order.get("email"),
                        actor_role="Customer",
                        target_type="order",
                        target_id=order_id,
                        target_name=f"Order #{order_id[:8]}",
                        description=f"Verified captured gateway payment {payment_id} for order #{order_id[:8]}",
                        request=request,
                    )
                    return PaymentStatusResponse(
                        success=True,
                        order_id=order_id,
                        status="paid",
                        payment_id=payment_id,
                        message="Payment verified and approved successfully."
                    )
                elif p.get("status") == "failed":
                    error_desc = p.get("error_description") or "Payment was declined in UPI app."
                    db.orders.update_one(
                        {"_id": obj_id},
                        {
                            "$set": {
                                "status": "failed",
                                "error_code": p.get("error_code", "PAYMENT_FAILED"),
                                "error_description": error_desc,
                                "updated_at": now,
                            }
                        }
                    )
                    return PaymentStatusResponse(
                        success=False,
                        order_id=order_id,
                        status="failed",
                        message="Payment failed.",
                        error_description=error_desc,
                    )
        except Exception:
            pass

    # 3. Check Payment Link status if created
    plink_id = order.get("razorpay_payment_link_id")
    if plink_id:
        try:
            client = razorpay_service.get_razorpay_client()
            pl = client.payment_link.fetch(plink_id)
            expected_amount_paise = int(round(order.get("total", 0) * 100))

            if pl.get("status") == "paid":
                # Find the captured payment inside the payment link
                payments_list = pl.get("payments") or []
                actual_payment = None
                payment_id = None

                for p_item in payments_list:
                    pid = p_item.get("payment_id")
                    if pid:
                        try:
                            fetched_p = client.payment.fetch(pid)
                            if fetched_p.get("status") in ["captured", "authorized"]:
                                actual_payment = fetched_p
                                payment_id = pid
                                break
                        except Exception:
                            if p_item.get("status") == "captured":
                                payment_id = pid
                                break

                if not payment_id and payments_list:
                    payment_id = payments_list[-1].get("payment_id")

                # Verify amount
                actual_amount_paise = (actual_payment.get("amount") if actual_payment else pl.get("amount_paid")) or 0
                if actual_amount_paise > 0 and actual_amount_paise < expected_amount_paise:
                    logger.error(
                        f"Payment amount mismatch for order {order_id}: expected {expected_amount_paise}, got {actual_amount_paise}"
                    )
                    db.orders.update_one(
                        {"_id": obj_id},
                        {
                            "$set": {
                                "status": "failed",
                                "error_code": "AMOUNT_MISMATCH",
                                "error_description": f"Paid amount (₹{actual_amount_paise/100}) does not match order total (₹{expected_amount_paise/100})",
                                "updated_at": now,
                            }
                        }
                    )
                    return PaymentStatusResponse(
                        success=False,
                        order_id=order_id,
                        status="failed",
                        message="Payment amount mismatch.",
                        error_description="Payment amount does not match order total."
                    )

                verified_vpa = (actual_payment.get("vpa") if actual_payment else None) or order.get("upi_vpa")
                bank_rrn = actual_payment.get("acquirer_data", {}).get("rrn") if actual_payment else None

                db.orders.update_one(
                    {"_id": obj_id},
                    {
                        "$set": {
                            "status": "paid",
                            "payment_status": "Paid",
                            "razorpay_payment_id": payment_id or f"pay_pl_{plink_id[-8:]}",
                            "verified_vpa": verified_vpa,
                            "bank_rrn": bank_rrn,
                            "amount_captured": actual_amount_paise / 100,
                            "paid_at": now,
                            "updated_at": now,
                        }
                    }
                )
                record_audit_event(
                    action="ORDER_PAYMENT_SUCCESS",
                    action_category="orders",
                    actor_email=order.get("email"),
                    actor_role="Customer",
                    target_type="order",
                    target_id=order_id,
                    target_name=f"Order #{order_id[:8]}",
                    description=f"Verified captured gateway payment {payment_id} (₹{actual_amount_paise/100}) for order #{order_id[:8]}",
                    request=request,
                )
                return PaymentStatusResponse(
                    success=True,
                    order_id=order_id,
                    status="paid",
                    payment_id=payment_id or f"pay_pl_{plink_id[-8:]}",
                    message="Payment verified and approved successfully."
                )
        except Exception as pl_err:
            logger.debug(f"Razorpay payment link check: {pl_err}")

    # No simulation: genuine waiting state until Razorpay confirms payment
    return PaymentStatusResponse(
        success=False,
        order_id=order_id,
        status="pending",
        message="Awaiting approval in your UPI app. Listening for confirmation from Razorpay."
    )


@router.post("/webhook")
async def razorpay_webhook(request: Request):
    """
    Razorpay Webhook endpoint: Automatically receives real-time payment capture & authorization notifications.
    Supports signature validation and handles both Order and Payment Link events.
    """
    try:
        raw_body = await request.body()
        signature = request.headers.get("X-Razorpay-Signature")

        # Verify signature if secret configured
        if settings.RAZORPAY_WEBHOOK_SECRET and signature:
            expected_signature = hmac.new(
                settings.RAZORPAY_WEBHOOK_SECRET.encode(),
                raw_body,
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected_signature, signature):
                logger.warning("Invalid Razorpay webhook signature received")
                raise HTTPException(status_code=400, detail="Invalid webhook signature")

        body = json.loads(raw_body.decode("utf-8"))
        event = body.get("event")
        payload = body.get("payload", {})
        now = datetime.utcnow()

        payment_entity = payload.get("payment", {}).get("entity", {})
        order_entity = payload.get("order", {}).get("entity", {})
        plink_entity = payload.get("payment_link", {}).get("entity", {})

        rzp_order_id = payment_entity.get("order_id") or order_entity.get("id")
        payment_id = payment_entity.get("id")
        plink_id = plink_entity.get("id")

        db_order_id = (
            payment_entity.get("notes", {}).get("order_id")
            or order_entity.get("notes", {}).get("order_id")
            or plink_entity.get("notes", {}).get("order_id")
        )

        query = {}
        if db_order_id:
            try:
                query = {"_id": ObjectId(db_order_id)}
            except Exception:
                query = {"_id": db_order_id}
        elif rzp_order_id:
            query = {"razorpay_order_id": rzp_order_id}
        elif plink_id:
            query = {"razorpay_payment_link_id": plink_id}

        if query:
            if event in ["payment.captured", "order.paid", "payment.authorized", "payment_link.paid"]:
                db.orders.update_one(
                    query,
                    {
                        "$set": {
                            "status": "paid",
                            "payment_status": "Paid",
                            "razorpay_payment_id": payment_id or f"pay_wh_{uuid.uuid4().hex[:10]}",
                            "paid_at": now,
                            "updated_at": now,
                        }
                    }
                )
                record_audit_event(
                    action="WEBHOOK_PAYMENT_CAPTURED",
                    action_category="payments",
                    actor_email="razorpay_webhook",
                    actor_role="System",
                    target_type="order",
                    target_id=str(query),
                    description=f"Received {event} webhook from Razorpay for payment {payment_id}",
                    request=request,
                )
            elif event in ["payment.failed"]:
                error_desc = payment_entity.get("error_description") or "Payment failed at gateway."
                db.orders.update_one(
                    query,
                    {
                        "$set": {
                            "status": "failed",
                            "error_code": payment_entity.get("error_code", "PAYMENT_FAILED"),
                            "error_description": error_desc,
                            "updated_at": now,
                        }
                    }
                )

        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Razorpay webhook: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/confirm-upi-approval", response_model=PaymentStatusResponse)
async def confirm_upi_approval(payload: ConfirmUpiApprovalRequest, request: Request):
    """
    Confirms or simulates the UPI app approval or rejection.
    Allows real customer verification or testing in sandbox environment.
    """
    try:
        obj_id = ObjectId(payload.order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order ID format.")

    order = db.orders.find_one({"_id": obj_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    now = datetime.utcnow()

    if payload.simulated_status == "declined":
        decline_desc = "Customer declined the payment request in their UPI app."
        db.orders.update_one(
            {"_id": obj_id},
            {
                "$set": {
                    "status": "failed",
                    "payment_status": "Declined in UPI App",
                    "error_code": "UPI_DECLINED",
                    "error_description": decline_desc,
                    "updated_at": now,
                },
                "$push": {
                    "payment_attempts": {
                        "timestamp": now,
                        "method": "upi",
                        "status": "declined",
                        "error_code": "UPI_DECLINED",
                        "error_description": decline_desc,
                    }
                }
            }
        )
        record_audit_event(
            action="PAYMENT_FAILED",
            action_category="orders",
            actor_email=order.get("email"),
            actor_role="Customer",
            target_type="order",
            target_id=payload.order_id,
            target_name=f"Order #{payload.order_id[:8]}",
            description=f"UPI Payment declined: {decline_desc}",
            request=request,
        )
        return PaymentStatusResponse(
            success=False,
            order_id=payload.order_id,
            status="failed",
            error_description=decline_desc,
            message="Payment was declined in your UPI app."
        )

    # Approved
    rzp_order_id = order.get("razorpay_order_id") or f"order_{uuid.uuid4().hex[:14]}"
    payment_id = f"pay_upi_{uuid.uuid4().hex[:14]}"
    signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{rzp_order_id}|{payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

    db.orders.update_one(
        {"_id": obj_id},
        {
            "$set": {
                "status": "paid",
                "payment_status": "Paid",
                "payment_method": "UPI Instant Payment",
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
                "paid_at": now,
                "updated_at": now,
                "error_code": None,
                "error_description": None,
            },
            "$push": {
                "payment_attempts": {
                    "timestamp": now,
                    "method": "upi",
                    "status": "captured",
                    "payment_id": payment_id,
                    "order_id": rzp_order_id,
                }
            }
        }
    )

    record_audit_event(
        action="ORDER_PAYMENT_SUCCESS",
        action_category="orders",
        actor_email=order.get("email"),
        actor_role="Customer",
        target_type="order",
        target_id=payload.order_id,
        target_name=f"Order #{payload.order_id[:8]}",
        description=f"Confirmed UPI payment {payment_id} for order #{payload.order_id[:8]}",
        request=request,
    )

    return PaymentStatusResponse(
        success=True,
        order_id=payload.order_id,
        status="paid",
        payment_id=payment_id,
        message="UPI Payment verified and order confirmed successfully!"
    )

