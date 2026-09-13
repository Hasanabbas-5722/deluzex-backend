from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app import models
from app.api.deps import get_current_active_admin
from app.services.imagekit import upload_image_to_imagekit
from app.core.database import db

router = APIRouter()

DEFAULT_TESTIMONIALS = [
    {
        "author_name": "Anna Clark",
        "author_title": "Interior Designer",
        "text": "The quality and craftsmanship are truly exceptional. The chandelier we chose became the highlight of our home.",
        "rating": 5.0,
        "avatar_url": "/images/avatar_woman_1784107804209.jpg",
        "created_at": datetime.utcnow()
    },
    {
        "author_name": "David Miller",
        "author_title": "Architect, Studio Form",
        "text": "De Luzex fixtures provide the exact color temperature and architectural finish our luxury residential clients demand.",
        "rating": 5.0,
        "avatar_url": "/images/avatar_woman_1784107804209.jpg",
        "created_at": datetime.utcnow()
    },
    {
        "author_name": "Sophia Reynolds",
        "author_title": "Homeowner, Mumbai",
        "text": "From packaging to final installation, the experience was seamless. The warm illumination completely transformed our living room.",
        "rating": 5.0,
        "avatar_url": "/images/avatar_woman_1784107804209.jpg",
        "created_at": datetime.utcnow()
    },
    {
        "author_name": "Marcus Vance",
        "author_title": "Hospitality Consultant",
        "text": "We specified De Luzex COB and pendant luminaires for a boutique hotel lobby. The feedback from guests has been phenomenal.",
        "rating": 4.8,
        "avatar_url": "/images/avatar_woman_1784107804209.jpg",
        "created_at": datetime.utcnow()
    }
]

@router.get("", response_model=List[models.Testimonial])
def get_testimonials(skip: int = 0, limit: int = 100):
    """
    Fetch all customer testimonials for the home page.
    Auto-seeds default testimonials if database collection is empty.
    """
    count = db.testimonials.count_documents({})
    if count == 0:
        db.testimonials.insert_many([dict(item) for item in DEFAULT_TESTIMONIALS])

    docs = list(db.testimonials.find().sort("created_at", -1).skip(skip).limit(limit))
    return [models.Testimonial(**doc) for doc in docs]

@router.get("/{testimonial_id}", response_model=models.Testimonial)
def get_testimonial(testimonial_id: str):
    try:
        obj_id = ObjectId(testimonial_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid testimonial ID format")

    doc = db.testimonials.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Testimonial not found")
    return models.Testimonial(**doc)

@router.post("", response_model=models.Testimonial)
async def create_testimonial(
    author_name: str = Form(...),
    text: str = Form(...),
    author_title: Optional[str] = Form(None),
    rating: float = Form(5.0),
    avatar_url: Optional[str] = Form(None),
    avatar_file: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(get_current_active_admin)
):
    final_avatar = avatar_url
    if avatar_file:
        try:
            final_avatar = await upload_image_to_imagekit(avatar_file, folder="/testimonials")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Avatar upload failed: {str(e)}")

    if not final_avatar:
        final_avatar = "/images/avatar_woman_1784107804209.jpg"

    item = models.Testimonial(
        author_name=author_name.strip(),
        author_title=author_title.strip() if author_title else None,
        text=text.strip(),
        rating=max(1.0, min(5.0, float(rating))),
        avatar_url=final_avatar.strip(),
        created_at=datetime.utcnow()
    )

    result = db.testimonials.insert_one(item.model_dump(by_alias=True, exclude_none=True))
    item.id = str(result.inserted_id)
    return item

@router.put("/{testimonial_id}", response_model=models.Testimonial)
async def update_testimonial(
    testimonial_id: str,
    author_name: Optional[str] = Form(None),
    author_title: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    rating: Optional[float] = Form(None),
    avatar_url: Optional[str] = Form(None),
    avatar_file: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(get_current_active_admin)
):
    try:
        obj_id = ObjectId(testimonial_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid testimonial ID format")

    doc = db.testimonials.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Testimonial not found")

    item = models.Testimonial(**doc)

    if author_name is not None:
        item.author_name = author_name.strip()
    if author_title is not None:
        item.author_title = author_title.strip()
    if text is not None:
        item.text = text.strip()
    if rating is not None:
        item.rating = max(1.0, min(5.0, float(rating)))

    if avatar_file:
        try:
            item.avatar_url = await upload_image_to_imagekit(avatar_file, folder="/testimonials")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Avatar upload failed: {str(e)}")
    elif avatar_url is not None and avatar_url.strip():
        item.avatar_url = avatar_url.strip()

    update_data = item.model_dump(by_alias=True, exclude={"id", "_id"})
    db.testimonials.update_one({"_id": obj_id}, {"$set": update_data})
    item.id = str(obj_id)
    return item

@router.delete("/{testimonial_id}")
def delete_testimonial(
    testimonial_id: str,
    current_user: models.User = Depends(get_current_active_admin)
):
    try:
        obj_id = ObjectId(testimonial_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid testimonial ID format")

    result = db.testimonials.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Testimonial not found")

    return {"message": "Testimonial deleted successfully", "id": testimonial_id}
