from dotenv.main import logger
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
from app import models
from app.api.deps import get_current_active_user, get_current_active_admin
from app.services.imagekit import upload_image_to_imagekit
from app.core.database import db
from app.core.audit import record_audit_event
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
        query["is_new_arrival"] = is_new_arrival

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
    product_price: float = Form(...),
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
    sku: Optional[str] = Form(None),
    stock_status: Optional[str] = Form("IN STOCK"),
    in_stock: Optional[bool] = Form(True),
    price_prefix: Optional[str] = Form("From"),
    price_note: Optional[str] = Form("per piece (volume contract applicable)"),
    dimensions: Optional[str] = Form(None),
    finish: Optional[str] = Form(None),
    material: Optional[str] = Form(None),
    colorway: Optional[str] = Form(None),
    piece_weight: Optional[str] = Form(None),
    care: Optional[str] = Form(None),
    moq_rule: Optional[str] = Form(None),
    replenishment: Optional[str] = Form(None),
    whatsapp_number: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    specifications: Optional[str] = Form(None),
    request: Request = None,
    current_user: models.User = Depends(get_current_active_admin)
):
    try:
        image_url = None
        product_images_urls = []
        if product_main_image:
            try:
                image_url = await upload_image_to_imagekit(product_main_image)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Main image upload failed: {str(e)}")
        
        if product_images:
            try:
                for img in product_images:
                    img_url = await upload_image_to_imagekit(img)
                    product_images_urls.append(img_url)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Gallery image upload failed: {str(e)}")

        parsed_specs = []
        if specifications:
            try:
                parsed_specs = json.loads(specifications)
            except Exception:
                pass
        
        product = models.Product(
            product_title=product_title,
            product_price=product_price,
            product_description=product_description,
            product_category=product_category,
            product_material=product_material or material,
            product_voltage=product_voltage,
            product_style=product_style,
            product_finishing=product_finishing or finish,
            stock_count=stock_count,
            is_featured=is_featured,
            is_new_arrival=is_new_arrival,
            product_main_image=image_url,
            product_images=product_images_urls,
            sku=sku,
            stock_status=stock_status,
            in_stock=in_stock,
            price_prefix=price_prefix,
            price_note=price_note,
            dimensions=dimensions,
            finish=finish or product_finishing,
            material=material or product_material,
            colorway=colorway,
            piece_weight=piece_weight,
            care=care,
            moq_rule=moq_rule,
            replenishment=replenishment,
            whatsapp_number=whatsapp_number,
            phone_number=phone_number,
            specifications=parsed_specs if isinstance(parsed_specs, list) else []
        )
        
        result = db.products.insert_one(product.model_dump(by_alias=True, exclude_none=True))
        product.id = str(result.inserted_id)

        record_audit_event(
            action="PRODUCT_CREATE",
            action_category="catalog",
            actor_id=current_user.id,
            actor_email=current_user.email,
            actor_name=f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email,
            actor_role="Admin",
            target_type="product",
            target_id=product.id,
            target_name=product.product_title,
            description=f"Created product '{product.product_title}' (₹{product.product_price})",
            details=f"Category: {product.product_category or 'General'}, Stock: {product.stock_count}",
            changes={"after": {"title": product.product_title, "price": product.product_price, "stock": product.stock_count}},
            request=request
        )
        
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
    product_category: Optional[str] = Form(None),
    product_material: Optional[str] = Form(None),
    product_voltage: Optional[str] = Form(None),
    product_style: Optional[str] = Form(None),
    product_finishing: Optional[str] = Form(None),
    stock_count: Optional[int] = Form(None),
    is_featured: Optional[bool] = Form(None),
    is_new_arrival: Optional[bool] = Form(None),
    product_main_image: Optional[UploadFile] = File(None),
    product_images: Optional[List[UploadFile]] = File(None),
    existing_images: Optional[str] = Form(None),
    sku: Optional[str] = Form(None),
    stock_status: Optional[str] = Form(None),
    in_stock: Optional[bool] = Form(None),
    price_prefix: Optional[str] = Form(None),
    price_note: Optional[str] = Form(None),
    dimensions: Optional[str] = Form(None),
    finish: Optional[str] = Form(None),
    material: Optional[str] = Form(None),
    colorway: Optional[str] = Form(None),
    piece_weight: Optional[str] = Form(None),
    care: Optional[str] = Form(None),
    moq_rule: Optional[str] = Form(None),
    replenishment: Optional[str] = Form(None),
    whatsapp_number: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    specifications: Optional[str] = Form(None),
    request: Request = None,
    current_user: models.User = Depends(get_current_active_admin)
):
    try:
        obj_id = ObjectId(product_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid product_id format")

    doc = db.products.find_one({"_id": obj_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Product not found")

    old_state = {
        "title": doc.get("product_title"),
        "price": doc.get("product_price"),
        "stock": doc.get("stock_count"),
        "is_featured": doc.get("is_featured"),
        "is_new_arrival": doc.get("is_new_arrival")
    }

    product = models.Product(**doc)

    if product_title is not None: product.product_title = product_title
    if product_price is not None: product.product_price = product_price
    if product_description is not None: product.product_description = product_description
    if product_category is not None: product.product_category = product_category
    if product_material is not None: product.product_material = product_material
    if product_voltage is not None: product.product_voltage = product_voltage
    if product_style is not None: product.product_style = product_style
    if product_finishing is not None: product.product_finishing = product_finishing
    if stock_count is not None: product.stock_count = stock_count
    if is_featured is not None: product.is_featured = is_featured
    if is_new_arrival is not None: product.is_new_arrival = is_new_arrival

    if sku is not None: product.sku = sku
    if stock_status is not None: product.stock_status = stock_status
    if in_stock is not None: product.in_stock = in_stock
    if price_prefix is not None: product.price_prefix = price_prefix
    if price_note is not None: product.price_note = price_note
    if dimensions is not None: product.dimensions = dimensions
    if finish is not None: 
        product.finish = finish
        if not product_finishing: product.product_finishing = finish
    if material is not None: 
        product.material = material
        if not product_material: product.product_material = material
    if colorway is not None: product.colorway = colorway
    if piece_weight is not None: product.piece_weight = piece_weight
    if care is not None: product.care = care
    if moq_rule is not None: product.moq_rule = moq_rule
    if replenishment is not None: product.replenishment = replenishment
    if whatsapp_number is not None: product.whatsapp_number = whatsapp_number
    if phone_number is not None: product.phone_number = phone_number

    if specifications is not None:
        try:
            parsed_specs = json.loads(specifications)
            if isinstance(parsed_specs, list):
                product.specifications = parsed_specs
        except Exception:
            pass

    if product_main_image:
        try:
            image_url = await upload_image_to_imagekit(product_main_image)
            product.product_main_image = image_url
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")

    updated_images = list(product.product_images or [])
    if existing_images is not None:
        try:
            parsed_existing = json.loads(existing_images)
            if isinstance(parsed_existing, list):
                updated_images = [img for img in parsed_existing if img]
        except Exception:
            pass

    if product_images:
        for img in product_images:
            try:
                img_url = await upload_image_to_imagekit(img)
                updated_images.append(img_url)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Gallery upload failed: {str(e)}")

    product.product_images = updated_images

    # Save to db
    update_data = product.model_dump(by_alias=True, exclude_none=True)
    update_data.pop("_id", None)
    db.products.update_one({"_id": obj_id}, {"$set": update_data})

    new_state = {
        "title": product.product_title,
        "price": product.product_price,
        "stock": product.stock_count,
        "is_featured": product.is_featured,
        "is_new_arrival": product.is_new_arrival
    }

    record_audit_event(
        action="PRODUCT_UPDATE",
        action_category="catalog",
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_name=f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email,
        actor_role="Admin",
        target_type="product",
        target_id=str(obj_id),
        target_name=product.product_title,
        description=f"Updated product details for '{product.product_title}'",
        changes={"before": old_state, "after": new_state},
        request=request
    )
    
    return product


class NewArrivalToggle(BaseModel):
    is_new_arrival: Optional[bool] = None

@router.patch("/{product_id}/new-arrival")
def toggle_new_arrival(
    product_id: str,
    payload: Optional[NewArrivalToggle] = None,
    is_new_arrival: Optional[bool] = None,
    request: Request = None,
    current_user: models.User = Depends(get_current_active_admin)
):
    try:
        obj_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product_id format")

    doc = db.products.find_one({"_id": obj_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if payload is not None and payload.is_new_arrival is not None:
        target_val = payload.is_new_arrival
    elif is_new_arrival is not None:
        target_val = is_new_arrival
    else:
        target_val = not doc.get("is_new_arrival", False)

    db.products.update_one({"_id": obj_id}, {"$set": {"is_new_arrival": target_val}})
    doc["is_new_arrival"] = target_val

    record_audit_event(
        action="PRODUCT_UPDATE",
        action_category="catalog",
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_name=f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email,
        actor_role="Admin",
        target_type="product",
        target_id=str(obj_id),
        target_name=doc.get("product_title"),
        description=f"Toggled New Arrival status to {target_val} for '{doc.get('product_title')}'",
        changes={"before": {"is_new_arrival": not target_val}, "after": {"is_new_arrival": target_val}},
        request=request
    )

    return models.Product(**doc)

@router.delete("/{product_id}")
def delete_product(
    product_id: str,
    request: Request = None,
    current_user: models.User = Depends(get_current_active_admin)
):
    try:
        obj_id = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product_id format")

    doc = db.products.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")

    result = db.products.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")

    record_audit_event(
        action="PRODUCT_DELETE",
        action_category="catalog",
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_name=f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email,
        actor_role="Admin",
        target_type="product",
        target_id=str(obj_id),
        target_name=doc.get("product_title"),
        description=f"Permanently deleted product '{doc.get('product_title')}'",
        changes={"before": {"title": doc.get("product_title"), "price": doc.get("product_price")}},
        request=request
    )

    return {"success": True, "message": "Product deleted successfully"}


