import logging
import re
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import models
from app.api.deps import get_current_active_user
from app.core.database import db
from app.schemas.order import (
    OrderCancelResponse,
    OrderCreateRequest,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdateRequest,
)

logger = logging.getLogger("uvicorn.error")

router = APIRouter()


def _format_order(doc: dict) -> dict:
    """Format MongoDB order document for response serialization."""
    doc["_id"] = str(doc["_id"])
    return doc


@router.get("/my-orders", response_model=List[models.Order])
def get_my_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Get all orders for the currently authenticated user.
    Retrieves orders matching the user's email or user ID, sorted newest first.
    """
    logger.info(f"[GET /my-orders] Fetching orders for user: email={current_user.email}, id={current_user.id}")
    conditions = []
    if current_user.email:
        conditions.append({"email": {"$regex": f"^{re.escape(current_user.email)}$", "$options": "i"}})
    if current_user.id:
        conditions.append({"user_id": str(current_user.id)})

    query = {"$or": conditions} if conditions else {}
    docs = list(
        db.orders.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    logger.info(f"[GET /my-orders] Found {len(docs)} orders for user {current_user.email}")
    return [models.Order(**doc) for doc in docs]


@router.get("", response_model=List[models.Order])
def list_orders(
    email: Optional[str] = Query(None, description="Filter by customer email"),
    phone: Optional[str] = Query(None, description="Filter by customer phone"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """
    Get orders with optional filters (email, phone, status) and pagination.
    Sorted newest first.
    """
    logger.info(f"[GET /orders] Listing orders with params: email={email}, phone={phone}, status={status}, skip={skip}, limit={limit}")
    query = {}
    if email:
        query["email"] = {"$regex": f"^{re.escape(email.strip())}$", "$options": "i"}
    if phone:
        query["phone"] = phone.strip()
    if status:
        query["status"] = {"$regex": f"^{re.escape(status.strip())}$", "$options": "i"}

    docs = list(
        db.orders.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    logger.info(f"[GET /orders] Query: {query} -> Found {len(docs)} orders")
    return [models.Order(**doc) for doc in docs]


@router.get("/{order_id}", response_model=models.Order)
def get_order(order_id: str):
    """
    Get full details of a specific order by its MongoDB Order ID.
    """
    logger.info(f"[GET /orders/{order_id}] Fetching order details")
    try:
        obj_id = ObjectId(order_id)
    except Exception:
        logger.warning(f"[GET /orders/{order_id}] Invalid ObjectId format")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID format",
        )

    doc = db.orders.find_one({"_id": obj_id})
    if doc is None:
        logger.warning(f"[GET /orders/{order_id}] Order not found in database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    logger.info(f"[GET /orders/{order_id}] Successfully retrieved order")
    return models.Order(**doc)


@router.post("", response_model=models.Order, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreateRequest):
    """
    Create a new order directly in the database.
    """
    initial_status = "cod" if payload.payment_method == "cod" else "pending"
    logger.info(f"[POST /orders] Creating order for email={payload.email}, total={payload.total}, payment_method={payload.payment_method}")

    db_order = models.Order(
        user_id=payload.user_id,
        email=payload.email,
        phone=payload.phone,
        shipping_address=payload.shipping_address,
        items=payload.items,
        subtotal=payload.subtotal,
        gst=payload.gst,
        delivery=payload.delivery,
        total=payload.total,
        payment_method=payload.payment_method,
        notes=payload.notes,
        status=initial_status,
        created_at=datetime.utcnow(),
    )

    result = db.orders.insert_one(
        db_order.model_dump(by_alias=True, exclude_none=True)
    )
    db_order.id = str(result.inserted_id)
    logger.info(f"[POST /orders] Created order with ID={db_order.id}")

    return db_order


@router.patch("/{order_id}/status", response_model=models.Order)
def update_order_status(order_id: str, payload: OrderStatusUpdateRequest):
    """
    Update the status, tracking number, or notes of an existing order.
    """
    logger.info(f"[PATCH /orders/{order_id}/status] Updating status to '{payload.status}'")
    try:
        obj_id = ObjectId(order_id)
    except Exception:
        logger.warning(f"[PATCH /orders/{order_id}/status] Invalid ObjectId format")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID format",
        )

    update_fields = {
        "status": payload.status,
        "updated_at": datetime.utcnow(),
    }
    if payload.tracking_number is not None:
        update_fields["tracking_number"] = payload.tracking_number
    if payload.notes is not None:
        update_fields["notes"] = payload.notes

    result = db.orders.update_one(
        {"_id": obj_id},
        {"$set": update_fields},
    )

    if result.matched_count == 0:
        logger.warning(f"[PATCH /orders/{order_id}/status] Order not found for update")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    doc = db.orders.find_one({"_id": obj_id})
    logger.info(f"[PATCH /orders/{order_id}/status] Status updated successfully")
    return models.Order(**doc)


@router.post("/{order_id}/cancel", response_model=OrderCancelResponse)
def cancel_order(order_id: str):
    """
    Cancel an order if it is in a cancellable state (pending, paid, cod, processing).
    """
    logger.info(f"[POST /orders/{order_id}/cancel] Attempting to cancel order")
    try:
        obj_id = ObjectId(order_id)
    except Exception:
        logger.warning(f"[POST /orders/{order_id}/cancel] Invalid ObjectId format")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID format",
        )

    doc = db.orders.find_one({"_id": obj_id})
    if doc is None:
        logger.warning(f"[POST /orders/{order_id}/cancel] Order not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    current_status = doc.get("status")
    non_cancellable = ["shipped", "out_for_delivery", "delivered", "cancelled"]
    if current_status in non_cancellable:
        logger.warning(f"[POST /orders/{order_id}/cancel] Cannot cancel order with status '{current_status}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order cannot be cancelled as it is already '{current_status}'",
        )

    db.orders.update_one(
        {"_id": obj_id},
        {
            "$set": {
                "status": "cancelled",
                "updated_at": datetime.utcnow(),
            }
        },
    )
    logger.info(f"[POST /orders/{order_id}/cancel] Order cancelled successfully")

    return OrderCancelResponse(
        success=True,
        order_id=order_id,
        message="Order cancelled successfully",
        status="cancelled",
    )
