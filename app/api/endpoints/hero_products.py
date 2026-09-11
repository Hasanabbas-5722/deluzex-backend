from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app import models
from app.api.deps import get_current_active_admin
from app.services.imagekit import upload_image_to_imagekit
from app.core.database import db

router = APIRouter()

DEFAULT_LAMPS = [
    {
        "image": "/images/lamp_modern_tall_1784107732736.jpg",
        "name": "Cylindrical Floor Lamp",
        "price": 231.0,
        "alt": "Modern gold cylinder floor lamp",
        "created_at": datetime.utcnow()
    },
    {
        "image": "/images/lamp_black_gold_1784107745696.jpg",
        "name": "Modern Black Desk Lamp",
        "price": 231.0,
        "alt": "Modern brass desk lamp with black lampshade",
        "created_at": datetime.utcnow()
    },
    {
        "image": "/images/lamp_classic_1784107722127.jpg",
        "name": "Vintage Pleated Lamp",
        "price": 231.0,
        "alt": "Vintage gold lamp with pleated shade",
        "created_at": datetime.utcnow()
    }
]

@router.get("", response_model=List[models.HeroProduct])
def get_hero_products():
    """
    Fetch all hero products for the homepage carousel.
    Auto-seeds default products if database collection is empty.
    """
    count = db.hero_products.count_documents({})
    if count == 0:
        db.hero_products.insert_many([dict(item) for item in DEFAULT_LAMPS])

    docs = list(db.hero_products.find().sort("created_at", 1))
    return [models.HeroProduct(**doc) for doc in docs]

@router.get("/{product_id}", response_model=models.HeroProduct)
def get_hero_product(product_id: str):
    try:
        obj_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID format")

    doc = db.hero_products.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Hero product not found")
    return models.HeroProduct(**doc)

@router.post("", response_model=models.HeroProduct)
async def create_hero_product(
    name: str = Form(...),
    price: float = Form(...),
    alt: str = Form(...),
    image: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(get_current_active_admin)
):
    final_image = image
    if image_file:
        try:
            final_image = await upload_image_to_imagekit(image_file, folder="/hero")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")

    if not final_image:
        raise HTTPException(status_code=400, detail="Either an image file or image URL is required")

    hero_item = models.HeroProduct(
        name=name.strip(),
        price=price,
        alt=alt.strip(),
        image=final_image.strip(),
        created_at=datetime.utcnow()
    )

    result = db.hero_products.insert_one(hero_item.model_dump(by_alias=True, exclude_none=True))
    hero_item.id = str(result.inserted_id)
    return hero_item

@router.put("/{product_id}", response_model=models.HeroProduct)
async def update_hero_product(
    product_id: str,
    name: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    alt: Optional[str] = Form(None),
    image: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(get_current_active_admin)
):
    try:
        obj_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID format")

    doc = db.hero_products.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Hero product not found")

    item = models.HeroProduct(**doc)

    if name is not None:
        item.name = name.strip()
    if price is not None:
        item.price = price
    if alt is not None:
        item.alt = alt.strip()
    if image is not None and image.strip():
        item.image = image.strip()

    if image_file:
        try:
            uploaded_url = await upload_image_to_imagekit(image_file, folder="/hero")
            item.image = uploaded_url
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")

    update_data = item.model_dump(by_alias=True, exclude_none=True)
    update_data.pop("_id", None)
    db.hero_products.update_one({"_id": obj_id}, {"$set": update_data})

    return item

@router.delete("/{product_id}")
def delete_hero_product(
    product_id: str,
    current_user: models.User = Depends(get_current_active_admin)
):
    try:
        obj_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID format")

    result = db.hero_products.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Hero product not found")

    return {"success": True, "message": "Hero product deleted successfully"}
