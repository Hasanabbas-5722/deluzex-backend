from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app import models
from app.core.database import db
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartSyncRequest

router = APIRouter()

def find_product_details(prod_id: str):
    """Safely find product in MongoDB, or return None if not present."""
    doc = None
    try:
        doc = db.products.find_one({"_id": ObjectId(prod_id)})
    except Exception:
        pass
    if not doc:
        doc = db.products.find_one({"$or": [{"id": prod_id}, {"_id": prod_id}, {"sku": prod_id}]})
    return doc

def build_cart_response(doc: dict) -> dict:
    """Build a rich, populated cart item response."""
    prod_id = str(doc.get("product_id"))
    prod = find_product_details(prod_id)
    
    title = (prod.get("product_title") if prod else None) or doc.get("title") or "Luxury Lighting Fixture"
    price = (float(prod.get("product_price", 0)) if prod and prod.get("product_price") is not None else None)
    if price is None:
        price = float(doc.get("price") or 0.0)
    image = (prod.get("product_main_image") if prod else None) or doc.get("image") or "/images/lamp_modern_tall_1784107732736.jpg"
    stock = prod.get("stock_count", 99) if prod else 99
    
    return {
        "id": str(doc.get("_id", prod_id)),
        "product_id": prod_id,
        "title": title,
        "price": price,
        "image": image,
        "quantity": int(doc.get("quantity", 1)),
        "stock": stock,
        "session_id": doc.get("session_id"),
        "user_email": doc.get("user_email")
    }

@router.get("/{identifier}")
def get_cart(identifier: str):
    """Retrieve all cart items for a session_id or user_email."""
    docs = list(db.cart_items.find({
        "$or": [
            {"session_id": identifier},
            {"user_email": identifier}
        ]
    }))
    return [build_cart_response(doc) for doc in docs]

@router.post("/add")
def add_to_cart(item: CartItemCreate):
    """Add item to cart or increment quantity if already in cart."""
    prod_id = str(item.product_id).strip()
    
    query = {
        "product_id": prod_id,
        "$or": [{"session_id": item.session_id}]
    }
    if item.user_email:
        query["$or"].append({"user_email": item.user_email})
        
    existing = db.cart_items.find_one(query)
    
    now = datetime.utcnow()
    if existing:
        db.cart_items.update_one(
            {"_id": existing["_id"]},
            {
                "$inc": {"quantity": item.quantity},
                "$set": {
                    "updated_at": now,
                    "user_email": item.user_email or existing.get("user_email"),
                    "title": item.title or existing.get("title"),
                    "price": item.price if item.price is not None else existing.get("price"),
                    "image": item.image or existing.get("image")
                }
            }
        )
        updated = db.cart_items.find_one({"_id": existing["_id"]})
        return build_cart_response(updated)
    else:
        new_doc = {
            "session_id": item.session_id,
            "product_id": prod_id,
            "quantity": max(1, item.quantity),
            "user_email": item.user_email,
            "title": item.title,
            "price": item.price,
            "image": item.image,
            "created_at": now,
            "updated_at": now
        }
        res = db.cart_items.insert_one(new_doc)
        new_doc["_id"] = res.inserted_id
        return build_cart_response(new_doc)

@router.put("/{identifier}/items/{product_id}")
def update_cart_item(identifier: str, product_id: str, body: CartItemUpdate):
    """Update item quantity in cart. If quantity <= 0, item is removed."""
    prod_id = str(product_id).strip()
    
    query = {
        "product_id": prod_id,
        "$or": [{"session_id": identifier}, {"user_email": identifier}]
    }
    
    if body.quantity <= 0:
        db.cart_items.delete_one(query)
        return {"success": True, "message": "Item removed", "quantity": 0}
        
    db.cart_items.update_one(
        query,
        {
            "$set": {
                "quantity": body.quantity,
                "updated_at": datetime.utcnow()
            }
        }
    )
    updated = db.cart_items.find_one(query)
    if not updated:
        raise HTTPException(status_code=404, detail="Cart item not found")
    return build_cart_response(updated)

@router.delete("/{identifier}/items/{product_id}")
def remove_cart_item(identifier: str, product_id: str):
    """Remove a single item from the cart."""
    prod_id = str(product_id).strip()
    result = db.cart_items.delete_one({
        "product_id": prod_id,
        "$or": [{"session_id": identifier}, {"user_email": identifier}]
    })
    return {"success": True, "deleted_count": result.deleted_count}

@router.delete("/{identifier}")
def clear_cart(identifier: str):
    """Clear all items in the cart for a session or user."""
    result = db.cart_items.delete_many({
        "$or": [{"session_id": identifier}, {"user_email": identifier}]
    })
    return {"success": True, "deleted_count": result.deleted_count}

@router.post("/sync")
def sync_cart(body: CartSyncRequest):
    """Merge guest session cart into user account cart upon login."""
    guest_items = list(db.cart_items.find({"session_id": body.session_id}))
    now = datetime.utcnow()
    
    for item in guest_items:
        prod_id = str(item.get("product_id"))
        user_item = db.cart_items.find_one({
            "product_id": prod_id,
            "user_email": body.user_email
        })
        
        if user_item:
            # Merge quantity
            db.cart_items.update_one(
                {"_id": user_item["_id"]},
                {
                    "$inc": {"quantity": item.get("quantity", 1)},
                    "$set": {"updated_at": now}
                }
            )
            # Remove guest duplicate
            db.cart_items.delete_one({"_id": item["_id"]})
        else:
            # Reassign guest item to user
            db.cart_items.update_one(
                {"_id": item["_id"]},
                {
                    "$set": {
                        "user_email": body.user_email,
                        "updated_at": now
                    }
                }
            )
            
    # Return merged cart
    merged = list(db.cart_items.find({"user_email": body.user_email}))
    return [build_cart_response(doc) for doc in merged]


