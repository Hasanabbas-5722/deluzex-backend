from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
from app import models
from app.api.deps import get_current_active_user
from app.services.imagekit import upload_image_to_imagekit
from app.core.database import db

router = APIRouter()

@router.get("")
def read_categories(skip: int = 0, limit: int = 100):
    docs = list(db.categories.find().skip(skip).limit(limit))
    return [models.Category(**doc) for doc in docs]

@router.post("")
async def create_category(
    name: str = Form(...),
    category_id: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(get_current_active_user)
):
    final_image_url = None
    if image_file:
        try:
            final_image_url = await upload_image_to_imagekit(image_file, folder="/categories")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")

    category = models.Category(
        name=name,
        category_id=category_id,
        image_url=final_image_url
    )
    
    result = db.categories.insert_one(category.model_dump(by_alias=True, exclude_none=True))
    category.id = str(result.inserted_id)
    return category
