from fastapi import APIRouter
from typing import List
from app import models

router = APIRouter()

@router.get("/{session_id}")
async def get_cart(session_id: str):
    return await models.CartItem.find(models.CartItem.session_id == session_id).to_list()

from app.schemas.cart import CartItemCreate
from beanie import PydanticObjectId
from fastapi import HTTPException

@router.post("/add")
async def add_to_cart(item: CartItemCreate):
    try:
        product_id = PydanticObjectId(item.product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product_id format")
    
    db_item = models.CartItem(
        session_id=item.session_id,
        product_id=product_id,
        quantity=item.quantity
    )
    await db_item.insert()
    return db_item
