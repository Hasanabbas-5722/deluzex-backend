from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
from bson import ObjectId
from app import models
from app.api.deps import get_current_active_admin
from app.services.imagekit import upload_image_to_imagekit
from app.core.database import db

router = APIRouter()

@router.get("", response_model=List[models.Category])
def read_categories(skip: int = 0, limit: int = 100):
    """
    Get all categories from MongoDB.
    """
    docs = list(db.categories.find().skip(skip).limit(limit))
    return [models.Category(**doc) for doc in docs]


@router.get("/{identifier}", response_model=models.Category)
def read_category(identifier: str):
    """
    Get a single category from MongoDB database by _id (ObjectId) or category_id or name.
    """
    doc = None
    if ObjectId.is_valid(identifier):
        doc = db.categories.find_one({"_id": ObjectId(identifier)})
    if not doc:
        doc = db.categories.find_one({"category_id": identifier})
    if not doc:
        doc = db.categories.find_one({"name": identifier})

    if not doc:
        raise HTTPException(status_code=404, detail="Category not found")

    return models.Category(**doc)


@router.post("", response_model=models.Category)
async def create_category(
    name: str = Form(...),
    category_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_active_admin)
):
    """
    Create a new category in MongoDB.
    """
    final_image_url = image_url
    if image_file:
        try:
            final_image_url = await upload_image_to_imagekit(image_file, folder="/categories")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")

    cat_id = category_id or name.strip().lower().replace(" ", "-")

    category_dict = {
        "name": name.strip(),
        "category_id": cat_id,
        "description": description.strip() if description else None,
        "image_url": final_image_url
    }
    
    result = db.categories.insert_one(category_dict)
    category_dict["_id"] = result.inserted_id
    return models.Category(**category_dict)


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
    Update an existing category in MongoDB by _id (ObjectId) or category_id.
    """
    query = None
    if ObjectId.is_valid(identifier):
        query = {"_id": ObjectId(identifier)}
    else:
        query = {"category_id": identifier}

    doc = db.categories.find_one(query)
    if not doc:
        doc = db.categories.find_one({"name": identifier})
        if doc:
            query = {"_id": doc["_id"]}

    if not doc:
        raise HTTPException(status_code=404, detail="Category not found")

    updates = {}
    if name is not None:
        updates["name"] = name.strip()
    if category_id is not None:
        updates["category_id"] = category_id.strip()
    if description is not None:
        updates["description"] = description.strip()
    if image_url is not None:
        updates["image_url"] = image_url
    if image:
        try:
            updates["image_url"] = await upload_image_to_imagekit(image, folder="/categories")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")

    if updates:
        db.categories.update_one({"_id": doc["_id"]}, {"$set": updates})
        doc = db.categories.find_one({"_id": doc["_id"]})

    return models.Category(**doc)


@router.delete("/{identifier}")
def delete_category(
    identifier: str,
    current_user: models.User = Depends(get_current_active_admin)
):
    """
    Delete a category from MongoDB database by _id (ObjectId) or category_id.
    """
    query = None
    if ObjectId.is_valid(identifier):
        query = {"_id": ObjectId(identifier)}
    else:
        query = {"category_id": identifier}

    result = db.categories.delete_one(query)
    if result.deleted_count == 0:
        result = db.categories.delete_one({"name": identifier})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")

    return {"message": "Category deleted successfully"}
