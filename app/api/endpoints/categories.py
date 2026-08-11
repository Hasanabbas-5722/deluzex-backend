from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
from beanie import PydanticObjectId
from app import models
from app.api.deps import get_current_active_user
from app.services.imagekit import upload_image_to_imagekit

router = APIRouter()

@router.get("", response_model=List[models.Category])
async def read_categories(skip: int = 0, limit: int = 100):
    """
    Get all categories from MongoDB database.
    """
    return await models.Category.find_all().skip(skip).limit(limit).to_list()


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
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Create a new category in MongoDB database.
    """
    final_image_url = image_url

    if image:
        try:
            final_image_url = await upload_image_to_imagekit(image, folder="/categories")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")

    category = models.Category(
        name=name,
        category_id=category_id,
        description=description,
        image_url=final_image_url
    )
    await category.insert()
    return category


@router.put("/{identifier}", response_model=models.Category)
async def update_category(
    identifier: str,
    name: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_active_user)
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
    current_user: models.User = Depends(get_current_active_user)
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

