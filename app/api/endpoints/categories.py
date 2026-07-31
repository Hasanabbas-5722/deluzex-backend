from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
from app import models
from app.api.deps import get_current_active_user
from app.services.imagekit import upload_image_to_imagekit

router = APIRouter()

@router.get("")
async def read_categories(skip: int = 0, limit: int = 100):
    return await models.Category.find_all().skip(skip).limit(limit).to_list()

@router.post("")
async def create_category(
    name: str = Form(...),
    category_id: Optional[str] = Form(None),
    image_url: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(get_current_active_user)
):
    image_url = None
    if image_url:
        try:
            image_url = await upload_image_to_imagekit(image_url, folder="/categories")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")

    category = models.Category(
        name=name,
        category_id=category_id,
        image_url=image_url
    )
    await category.insert()
    return category
