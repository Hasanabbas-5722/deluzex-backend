import hashlib
import hmac
import uuid
from typing import Optional

import razorpay

from app.core.config import settings

_client: Optional[razorpay.Client] = None


def get_razorpay_client() -> razorpay.Client:
    global _client
    if _client is None:
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            raise ValueError("Razorpay credentials are not configured")
        _client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    return _client


def create_razorpay_order(amount_paise: int, receipt: str, currency: str = "INR") -> dict:
    client = get_razorpay_client()
    return client.order.create(
        {
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
        }
    )


def verify_payment_signature(
    razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str
) -> bool:
    if not settings.RAZORPAY_KEY_SECRET:
        return False
    message = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    generated = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(), message, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(generated, razorpay_signature)


def generate_receipt() -> str:
    return f"rcpt_{uuid.uuid4().hex[:12]}"
