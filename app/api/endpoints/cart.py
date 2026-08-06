from fastapi import APIRouter, HTTPException
from typing import List
from app import models
from bson import ObjectId
from app.core.database import db
from app.schemas.cart import CartItemCreate

router = APIRouter()

@router.get("/{session_id}")
def get_cart(session_id: str):
    docs = list(db.cart_items.find({"session_id": session_id}))
    return [models.CartItem(**doc) for doc in docs]

@router.post("/add")
def add_to_cart(item: CartItemCreate):
    try:
        product_id = ObjectId(item.product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product_id format")
    
    db_item = models.CartItem(
        session_id=item.session_id,
        product_id=str(product_id),
        quantity=item.quantity
    )
    
    result = db.cart_items.insert_one(db_item.model_dump(by_alias=True, exclude_none=True))
    db_item.id = str(result.inserted_id)
    return db_item

