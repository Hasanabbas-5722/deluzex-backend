from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
from app import models
from app.api.deps import get_current_active_user, get_current_active_admin
from app.services.imagekit import upload_image_to_imagekit
from app.core.database import db

router = APIRouter()

@router.get("")
def read_categories(skip: int = 0, limit: int = 100):
    docs = list(db.categories.find().skip(skip).limit(limit))
    return [models.Category(**doc) for doc in docs]


@router.get("/{identifier}", response_model=models.Category)
async def read_category(identifier: str):
    """
    Get a single category from MongoDB database by _id (ObjectId) or category_id.
    """
    category = None
    
    # 1. Check if identifier is a valid MongoDB ObjectId
    if PydanticObjectId.is_valid(identifier):
        category = await models.Category.get(PydanticObjectId(identifier))

    # 2. If not found by ObjectId, search by custom category_id field
    if not category:
        category = await models.Category.find_one(models.Category.category_id == identifier)

    # 3. If still not found, search by name
    if not category:
        category = await models.Category.find_one(models.Category.name == identifier)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    return category


@router.post("", response_model=models.Category)
async def create_category(
    name: str = Form(...),
    category_id: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(get_current_active_admin)
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


@router.put("/{identifier}", response_model=models.Category)
async def update_category(
    identifier: str,
    name: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_active_admin)
):
    """
    Update an existing category by _id or category_id.
    """
    category = None
    if PydanticObjectId.is_valid(identifier):
        category = await models.Category.get(PydanticObjectId(identifier))
    if not category:
        category = await models.Category.find_one(models.Category.category_id == identifier)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if name is not None:
        category.name = name
    if category_id is not None:
        category.category_id = category_id
    if description is not None:
        category.description = description
    if image_url is not None:
        category.image_url = image_url
    if image:
        try:
            category.image_url = await upload_image_to_imagekit(image, folder="/categories")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")

    await category.save()
    return category


@router.delete("/{identifier}")
async def delete_category(
    identifier: str,
    current_user: models.User = Depends(get_current_active_admin)
):
    """
    Delete a category from MongoDB database by _id or category_id.
    """
    category = None
    if PydanticObjectId.is_valid(identifier):
        category = await models.Category.get(PydanticObjectId(identifier))
    if not category:
        category = await models.Category.find_one(models.Category.category_id == identifier)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    await category.delete()
    return {"message": "Category deleted successfully"}

