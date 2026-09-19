from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query, status
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from app import models
from app.api.deps import get_current_active_admin
from app.services.imagekit import upload_image_to_imagekit
from app.core.database import db

router = APIRouter()

DEFAULT_PROJECTS = [
    {
        "title": "Luxury Villa Residence",
        "location": "London, UK",
        "category": "Residential",
        "subtitle": "Bespoke Residential Lighting",
        "description": "Comprehensive architectural and decorative lighting plan featuring custom hand-blown chandeliers, perimeter COB downlights, and warm brass wall sconces across a private three-story villa.",
        "installations_count": "18 Bespoke Fixtures",
        "image_url": "/images/project_lounge_1784107767735.jpg",
        "gallery_images": [
            "/images/project_lounge_1784107767735.jpg",
            "/images/category_chandelier_1784107756268.jpg",
            "/images/about_chandelier_1784107790569.jpg"
        ],
        "is_featured": True,
        "sequence": 1,
        "created_at": datetime.utcnow()
    },
    {
        "title": "The Grand Hotel Lobby",
        "location": "Paris, France",
        "category": "Hospitality",
        "subtitle": "Grand Hospitality Illumination",
        "description": "Dramatic monumental crystal chandelier installation paired with anti-glare recessed architectural fixtures, elevating the double-height arrival lobby of a premier five-star destination.",
        "installations_count": "32 Architectural Fixtures",
        "image_url": "/images/project_lobby_1784107778993.jpg",
        "gallery_images": [
            "/images/project_lobby_1784107778993.jpg",
            "/images/lamp_modern_tall_1784107732736.jpg"
        ],
        "is_featured": True,
        "sequence": 2,
        "created_at": datetime.utcnow()
    },
    {
        "title": "Modern Penthouse",
        "location": "New York, USA",
        "category": "Residential",
        "subtitle": "Contemporary Sky Residence",
        "description": "Sculptural linear LED pendants and dimmable cove illumination harmonizing panoramic skyline views with warm, gallery-grade residential illumination.",
        "installations_count": "14 Custom Fixtures",
        "image_url": "/images/hero_bg_1784107713316.jpg",
        "gallery_images": [
            "/images/hero_bg_1784107713316.jpg"
        ],
        "is_featured": False,
        "sequence": 3,
        "created_at": datetime.utcnow()
    },
    {
        "title": "Boutique Restaurant",
        "location": "Milan, Italy",
        "category": "Commercial",
        "subtitle": "Intimate Fine Dining Lighting",
        "description": "Low-glare pinpoint tableside luminaires and bespoke brass fixtures cultivating an atmosphere of refined indulgence for Milanese gastronomes.",
        "installations_count": "20 Ambient Fixtures",
        "image_url": "/images/lamp_classic_1784107722127.jpg",
        "gallery_images": [
            "/images/lamp_classic_1784107722127.jpg"
        ],
        "is_featured": False,
        "sequence": 4,
        "created_at": datetime.utcnow()
    }
]

@router.get("", response_model=List[models.Project])
def read_projects(
    is_featured: Optional[bool] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    """
    Fetch all projects sorted by sequence and creation date.
    Auto-seeds default projects if database collection is empty.
    """
    count = db.projects.count_documents({})
    if count == 0:
        db.projects.insert_many([dict(item) for item in DEFAULT_PROJECTS])

    query: Dict[str, Any] = {}
    if is_featured is not None:
        query["is_featured"] = is_featured
    if category and category != "All" and category != "All Projects":
        query["category"] = category

    docs = list(db.projects.find(query).sort([("sequence", 1), ("created_at", -1)]).skip(skip).limit(limit))
    return [models.Project(**doc) for doc in docs]

@router.get("/{project_id}", response_model=models.Project)
def get_project(project_id: str):
    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    doc = db.projects.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")

    return models.Project(**doc)

@router.post("", response_model=models.Project)
async def create_project(
    title: str = Form(...),
    location: Optional[str] = Form(None),
    category: str = Form("Residential"),
    subtitle: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    installations_count: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    gallery_images: Optional[str] = Form(None),
    year: Optional[str] = Form(None),
    scope: Optional[str] = Form(None),
    area: Optional[str] = Form(None),
    client: Optional[str] = Form(None),
    is_featured: bool = Form(False),
    sequence: Optional[int] = Form(None),
    current_user: models.User = Depends(get_current_active_admin),
):
    final_image = image_url
    if image_file:
        try:
            final_image = await upload_image_to_imagekit(image_file, folder="/projects")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")

    if not final_image:
        final_image = "/images/project_lounge_1784107767735.jpg"

    if sequence is None or sequence <= 0:
        highest = db.projects.find_one(sort=[("sequence", -1)])
        sequence = (highest.get("sequence", 0) + 1) if highest else 1

    parsed_gallery: List[str] = []
    if gallery_images:
        try:
            import json
            val = json.loads(gallery_images)
            if isinstance(val, list):
                parsed_gallery = [str(v).strip() for v in val if v]
        except Exception:
            parsed_gallery = [img.strip() for img in gallery_images.split(",") if img.strip()]
    if final_image and final_image not in parsed_gallery:
        parsed_gallery.insert(0, final_image)

    project = models.Project(
        title=title.strip(),
        location=location.strip() if location else None,
        category=category.strip(),
        subtitle=subtitle.strip() if subtitle else None,
        description=description.strip() if description else None,
        installations_count=installations_count.strip() if installations_count else None,
        image_url=final_image.strip(),
        gallery_images=parsed_gallery,
        year=year.strip() if year else None,
        scope=scope.strip() if scope else None,
        area=area.strip() if area else None,
        client=client.strip() if client else None,
        is_featured=is_featured,
        sequence=sequence,
        created_at=datetime.utcnow(),
    )

    result = db.projects.insert_one(project.model_dump(by_alias=True, exclude_none=True))
    project.id = str(result.inserted_id)
    return project

@router.put("/{project_id}", response_model=models.Project)
async def update_project(
    project_id: str,
    title: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    subtitle: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    installations_count: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    gallery_images: Optional[str] = Form(None),
    year: Optional[str] = Form(None),
    scope: Optional[str] = Form(None),
    area: Optional[str] = Form(None),
    client: Optional[str] = Form(None),
    is_featured: Optional[bool] = Form(None),
    sequence: Optional[int] = Form(None),
    current_user: models.User = Depends(get_current_active_admin),
):
    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    doc = db.projects.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")

    project = models.Project(**doc)

    if title is not None and title.strip():
        project.title = title.strip()
    if location is not None:
        project.location = location.strip() if location.strip() else None
    if category is not None and category.strip():
        project.category = category.strip()
    if subtitle is not None:
        project.subtitle = subtitle.strip() if subtitle.strip() else None
    if description is not None:
        project.description = description.strip() if description.strip() else None
    if installations_count is not None:
        project.installations_count = installations_count.strip() if installations_count.strip() else None
    if year is not None:
        project.year = year.strip() if year.strip() else None
    if scope is not None:
        project.scope = scope.strip() if scope.strip() else None
    if area is not None:
        project.area = area.strip() if area.strip() else None
    if client is not None:
        project.client = client.strip() if client.strip() else None
    if is_featured is not None:
        project.is_featured = is_featured
    if sequence is not None:
        project.sequence = sequence

    if image_file:
        try:
            uploaded_url = await upload_image_to_imagekit(image_file, folder="/projects")
            project.image_url = uploaded_url
            if uploaded_url not in project.gallery_images:
                project.gallery_images.insert(0, uploaded_url)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")
    elif image_url is not None and image_url.strip():
        project.image_url = image_url.strip()

    if gallery_images is not None:
        try:
            import json
            val = json.loads(gallery_images)
            if isinstance(val, list):
                project.gallery_images = [str(v).strip() for v in val if v]
        except Exception:
            project.gallery_images = [img.strip() for img in gallery_images.split(",") if img.strip()]

    update_data = project.model_dump(by_alias=True, exclude_none=True)
    update_data.pop("_id", None)
    db.projects.update_one({"_id": obj_id}, {"$set": update_data})

    return project

@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    current_user: models.User = Depends(get_current_active_admin),
):
    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    result = db.projects.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"success": True, "message": "Project deleted successfully"}

@router.patch("/{project_id}/featured")
def toggle_project_featured(
    project_id: str,
    current_user: models.User = Depends(get_current_active_admin),
):
    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    doc = db.projects.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")

    new_featured = not doc.get("is_featured", False)
    db.projects.update_one({"_id": obj_id}, {"$set": {"is_featured": new_featured}})
    doc["is_featured"] = new_featured
    return models.Project(**doc)

@router.patch("/{project_id}/swap")
def swap_project_sequence(
    project_id: str,
    direction: str = Query(..., pattern="^(up|down)$"),
    current_user: models.User = Depends(get_current_active_admin),
):
    """
    1-Click Move Up or Move Down: Swaps sequence order with the adjacent project.
    """
    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    current_proj = db.projects.find_one({"_id": obj_id})
    if not current_proj:
        raise HTTPException(status_code=404, detail="Project not found")

    curr_seq = current_proj.get("sequence", 1)

    # Get all projects in sequence order
    all_projects = list(db.projects.find().sort([("sequence", 1), ("created_at", -1)]))
    idx = -1
    for i, p in enumerate(all_projects):
        if str(p["_id"]) == str(obj_id):
            idx = i
            break

    if idx == -1:
        raise HTTPException(status_code=404, detail="Project position not found")

    target_idx = idx - 1 if direction == "up" else idx + 1
    if target_idx < 0 or target_idx >= len(all_projects):
        # Already at top or bottom boundary
        return {"success": True, "message": "Already at boundary", "sequence": curr_seq}

    target_proj = all_projects[target_idx]
    target_seq = target_proj.get("sequence", 1)

    if target_seq == curr_seq:
        target_seq = curr_seq - 1 if direction == "up" else curr_seq + 1

    db.projects.update_one({"_id": current_proj["_id"]}, {"$set": {"sequence": target_seq}})
    db.projects.update_one({"_id": target_proj["_id"]}, {"$set": {"sequence": curr_seq}})

    return {
        "success": True,
        "message": f"Moved {direction} successfully",
        "swapped": {
            "current_id": str(current_proj["_id"]),
            "new_sequence": target_seq,
            "target_id": str(target_proj["_id"]),
            "target_sequence": curr_seq
        }
    }
