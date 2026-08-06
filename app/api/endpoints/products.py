from dotenv.main import logger
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
from bson import ObjectId
from app import models
from app.api.deps import get_current_active_user
from app.services.imagekit import upload_image_to_imagekit
from app.core.database import db
import json

router = APIRouter()

@router.get("")
def read_products(
    skip: int = 0,
    limit: int = 100,
    is_featured: Optional[bool] = None,
    is_new_arrival: Optional[bool] = None,
):
    query = {}

    if is_featured is not None:
        query["is_featured"] = is_featured

    if is_new_arrival is not None:
        if is_new_arrival:
            docs = list(db.products.find(query).sort("created_at", -1).limit(3))
            return [models.Product(**doc) for doc in docs]
            
    docs = list(db.products.find(query).skip(skip).limit(limit))
    return [models.Product(**doc) for doc in docs]

    
@router.get("/{product_id}")
def read_product(product_id: str):
    try:
        obj_id = ObjectId(product_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid product_id format")

    doc = db.products.find_one({"_id": obj_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return models.Product(**doc)

@router.post("")
async def create_product(
    product_title: str = Form(...),
    product_price: int = Form(...),
    product_description: Optional[str] = Form(None),
    product_category: Optional[str] = Form(None),
    product_material: Optional[str] = Form(None),
    product_voltage: Optional[str] = Form(None),
    product_style: Optional[str] = Form(None),
    product_finishing: Optional[str] = Form(None),
    stock_count: int = Form(0),
    is_featured: bool = Form(False),
    is_new_arrival: bool = Form(False),
    product_main_image: Optional[UploadFile] = File(None),
    product_images: Optional[List[UploadFile]] = File(None),
    current_user: models.User = Depends(get_current_active_user)
):
    try:
        image_url = None
        if product_main_image or product_images:
            try:
                if product_main_image:
                    image_url = await upload_image_to_imagekit(product_main_image)
                product_images_urls = []
                if product_images:
                    for img in product_images:
                        img_url = await upload_image_to_imagekit(img)
                        product_images_urls.append(img_url)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")
        logger.info(f"Product main image URL: {image_url}")
        
        product = models.Product(
            product_title=product_title,
            product_price=product_price,
            product_description=product_description,
            product_category=product_category,
            product_material=product_material,
            product_voltage=product_voltage,
            product_style=product_style,
            product_finishing=product_finishing,
            stock_count=stock_count,
            is_featured=is_featured,
            is_new_arrival=is_new_arrival,
            product_main_image=image_url,
            product_images=product_images_urls if product_images else []
        )
        
        result = db.products.insert_one(product.model_dump(by_alias=True, exclude_none=True))
        product.id = str(result.inserted_id)
        
        return product
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Product creation failed: {str(e)}")

@router.put("/{product_id}")
async def update_product(
    product_id: str,
    product_title: Optional[str] = Form(None),
    product_price: Optional[float] = Form(None),
    product_description: Optional[str] = Form(None),
    stock_count: Optional[int] = Form(None),
    is_featured: Optional[bool] = Form(None),
    is_new_arrival: Optional[bool] = Form(None),
    product_main_image: Optional[UploadFile] = File(None),
    product_images: Optional[List[UploadFile]] = File(None),
    current_user: models.User = Depends(get_current_active_user)
):
    try:
        obj_id = ObjectId(product_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid product_id format")

    doc = db.products.find_one({"_id": obj_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product = models.Product(**doc)

    if product_title is not None: product.product_title = product_title
    if product_price is not None: product.product_price = product_price
    if product_description is not None: product.product_description = product_description
    if stock_count is not None: product.stock_count = stock_count
    if is_featured is not None: product.is_featured = is_featured
    if is_new_arrival is not None: product.is_new_arrival = is_new_arrival

    if product_main_image:
        try:
            image_url = await upload_image_to_imagekit(product_main_image)
            product.product_main_image = image_url
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")

    if product_images:
        product_images_urls = []
        for img in product_images:
            img_url = await upload_image_to_imagekit(img)
            product_images_urls.append(img_url)
        product.product_images = product_images_urls

    # Save to db
    update_data = product.model_dump(by_alias=True, exclude_none=True)
    update_data.pop("_id", None)
    db.products.update_one({"_id": obj_id}, {"$set": update_data})
    
    return product

