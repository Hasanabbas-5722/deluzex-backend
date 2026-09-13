from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query, status
from typing import List, Optional, Dict, Any
from datetime import datetime
import re
from pydantic import BaseModel
from bson import ObjectId
from app import models
from app.api.deps import get_current_active_admin
from app.services.imagekit import upload_image_to_imagekit
from app.core.database import db

router = APIRouter()

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")

DEFAULT_BLOGS = [
    {
        "title": "How To Choose The Perfect Chandelier For Your Home",
        "slug": "how-to-choose-the-perfect-chandelier-for-your-home",
        "category": "Design & Inspiration",
        "author": "De Luzex",
        "read_time": "5 min read",
        "excerpt": "A comprehensive guide on selecting the right scale, luminescence warmth, and crystal finish for grand foyers and dining areas.",
        "content": "One of the most defining design choices in a luxury residence is selecting the perfect chandelier. Scale, ceiling proportion, and illumination temperature must harmonize seamlessly. When choosing a centerpiece, calculate the combined room dimensions to determine appropriate diameter, and ensure fixture drop leaves optimal clearance above dining or gathering surfaces.",
        "image": "/images/category_chandelier_1784107756268.jpg",
        "is_featured": True,
        "status": "Published",
        "sequence": 1,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "title": "The Art Of Layered Lighting in Modern Interiors",
        "slug": "the-art-of-layered-lighting-in-modern-interiors",
        "category": "Architectural Blogs",
        "author": "De Luzex",
        "read_time": "6 min read",
        "excerpt": "Learn how architectural downlights, accent sconces, and ambient pendants combine to create depth and emotional warmth.",
        "content": "Mastering architectural lighting requires balancing three core tiers: ambient, task, and accent. Diffused ambient illumination sets the visual baseline, task-oriented spots highlight functional zones, and warm grazing sconces reveal textured stonework and curated art pieces.",
        "image": "/images/about_chandelier_1784107790569.jpg",
        "is_featured": False,
        "status": "Published",
        "sequence": 2,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "title": "Architectural COB vs Decorative Lighting: Finding Equilibrium",
        "slug": "architectural-cob-vs-decorative-lighting-finding-equilibrium",
        "category": "Products Blogs",
        "author": "De Luzex",
        "read_time": "4 min read",
        "excerpt": "Understand beam angles, color rendering index (CRI 95+), and recessed baffle integration in high-end living spaces.",
        "content": "While decorative fixtures provide sculptural identity, architectural COB luminaires ensure functional illumination without visual glare. Specifying high CRI (>95) chips reproduces fabric hues, wood grains, and marble veining in their purest natural brilliance.",
        "image": "/images/lamp_classic_1784107722127.jpg",
        "is_featured": False,
        "status": "Published",
        "sequence": 3,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "title": "Lighting Scale & Proportion for Vaulted Ceilings",
        "slug": "lighting-scale-and-proportion-for-vaulted-ceilings",
        "category": "Design & Inspiration",
        "author": "De Luzex",
        "read_time": "5 min read",
        "excerpt": "How to suspend grand luminaires in double-height living rooms and stairwells without overwhelming sightlines.",
        "content": "Double-height spaces demand fixtures with vertical presence. A tiered silhouette anchored with bespoke brass rods draws the gaze upward, celebrating structural grandeur while casting a comforting, intimate perimeter glow below.",
        "image": "/images/project_lounge_1784107767735.jpg",
        "is_featured": False,
        "status": "Published",
        "sequence": 4,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
]

class ReorderItem(BaseModel):
    id: str
    sequence: int

@router.get("", response_model=List[models.Blog])
def get_blogs(
    category: Optional[str] = None,
    status: Optional[str] = None,
    is_featured: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
):
    """
    Fetch all blogs ordered strictly by sequence ascending, then created_at descending.
    Auto-seeds default blogs if collection is empty.
    """
    count = db.blogs.count_documents({})
    if count == 0:
        db.blogs.insert_many([dict(item) for item in DEFAULT_BLOGS])

    query: Dict[str, Any] = {}
    if category and category != "All" and category != "All Blogs":
        query["category"] = category
    if status:
        query["status"] = status
    if is_featured is not None:
        query["is_featured"] = is_featured

    docs = list(db.blogs.find(query).sort([("sequence", 1), ("created_at", -1)]).skip(skip).limit(limit))
    return [models.Blog(**doc) for doc in docs]

@router.get("/{id_or_slug}", response_model=models.Blog)
def get_blog(id_or_slug: str):
    """
    Fetch blog by ID or slug string.
    """
    doc = None
    if ObjectId.is_valid(id_or_slug):
        doc = db.blogs.find_one({"_id": ObjectId(id_or_slug)})

    if not doc:
        doc = db.blogs.find_one({"slug": id_or_slug})

    if not doc:
        raise HTTPException(status_code=404, detail="Blog not found")

    return models.Blog(**doc)

@router.post("", response_model=models.Blog)
async def create_blog(
    title: str = Form(...),
    category: str = Form("Design & Inspiration"),
    author: str = Form("De Luzex"),
    read_time: str = Form("5 min read"),
    excerpt: Optional[str] = Form(None),
    content: str = Form(...),
    image: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    is_featured: bool = Form(False),
    status: str = Form("Published"),
    sequence: Optional[int] = Form(None),
    slug: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_active_admin),
):
    final_image = image
    if image_file:
        try:
            final_image = await upload_image_to_imagekit(image_file, folder="/blogs")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")

    if not final_image:
        final_image = "/images/category_chandelier_1784107756268.jpg"

    base_slug = slugify(slug or title)
    unique_slug = base_slug
    counter = 1
    while db.blogs.find_one({"slug": unique_slug}):
        unique_slug = f"{base_slug}-{counter}"
        counter += 1

    # Determine sequence order
    if sequence is None or sequence <= 0:
        highest = db.blogs.find_one(sort=[("sequence", -1)])
        sequence = (highest.get("sequence", 0) + 1) if highest else 1

    blog_item = models.Blog(
        title=title.strip(),
        slug=unique_slug,
        category=category.strip(),
        author=author.strip(),
        read_time=read_time.strip(),
        excerpt=excerpt.strip() if excerpt else None,
        content=content.strip(),
        image=final_image.strip(),
        is_featured=is_featured,
        status=status.strip(),
        sequence=sequence,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    result = db.blogs.insert_one(blog_item.model_dump(by_alias=True, exclude_none=True))
    blog_item.id = str(result.inserted_id)
    return blog_item

@router.put("/{blog_id}", response_model=models.Blog)
async def update_blog(
    blog_id: str,
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    read_time: Optional[str] = Form(None),
    excerpt: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    image: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    is_featured: Optional[bool] = Form(None),
    status: Optional[str] = Form(None),
    sequence: Optional[int] = Form(None),
    slug: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_active_admin),
):
    try:
        obj_id = ObjectId(blog_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid blog ID format")

    doc = db.blogs.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Blog not found")

    blog = models.Blog(**doc)

    if title is not None and title.strip():
        blog.title = title.strip()
    if category is not None and category.strip():
        blog.category = category.strip()
    if author is not None and author.strip():
        blog.author = author.strip()
    if read_time is not None and read_time.strip():
        blog.read_time = read_time.strip()
    if excerpt is not None:
        blog.excerpt = excerpt.strip() if excerpt.strip() else None
    if content is not None and content.strip():
        blog.content = content.strip()
    if is_featured is not None:
        blog.is_featured = is_featured
    if status is not None and status.strip():
        blog.status = status.strip()
    if sequence is not None:
        blog.sequence = sequence
    if slug is not None and slug.strip():
        custom_slug = slugify(slug)
        existing = db.blogs.find_one({"slug": custom_slug, "_id": {"$ne": obj_id}})
        if not existing:
            blog.slug = custom_slug

    if image_file:
        try:
            uploaded_url = await upload_image_to_imagekit(image_file, folder="/blogs")
            blog.image = uploaded_url
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")
    elif image is not None and image.strip():
        blog.image = image.strip()

    blog.updated_at = datetime.utcnow()

    update_data = blog.model_dump(by_alias=True, exclude_none=True)
    update_data.pop("_id", None)
    db.blogs.update_one({"_id": obj_id}, {"$set": update_data})

    return blog

@router.delete("/{blog_id}")
def delete_blog(
    blog_id: str,
    current_user: models.User = Depends(get_current_active_admin),
):
    try:
        obj_id = ObjectId(blog_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid blog ID format")

    result = db.blogs.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Blog not found")

    return {"success": True, "message": "Blog deleted successfully"}

@router.patch("/reorder")
def reorder_blogs(
    items: List[ReorderItem],
    current_user: models.User = Depends(get_current_active_admin),
):
    """
    Batch update sequence numbers for a list of blogs.
    """
    for item in items:
        if ObjectId.is_valid(item.id):
            db.blogs.update_one({"_id": ObjectId(item.id)}, {"$set": {"sequence": item.sequence}})

    return {"success": True, "message": "Blog sequence updated successfully"}

@router.patch("/{blog_id}/swap")
def swap_blog_sequence(
    blog_id: str,
    direction: str = Query(..., pattern="^(up|down)$"),
    current_user: models.User = Depends(get_current_active_admin),
):
    """
    1-Click Move Up or Move Down: Swaps sequence order with the adjacent blog.
    """
    try:
        obj_id = ObjectId(blog_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid blog ID format")

    current_blog = db.blogs.find_one({"_id": obj_id})
    if not current_blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    curr_seq = current_blog.get("sequence", 1)

    # Get all blogs in sequence order
    all_blogs = list(db.blogs.find().sort([("sequence", 1), ("created_at", -1)]))
    idx = -1
    for i, b in enumerate(all_blogs):
        if str(b["_id"]) == str(obj_id):
            idx = i
            break

    if idx == -1:
        raise HTTPException(status_code=404, detail="Blog position not found")

    target_idx = idx - 1 if direction == "up" else idx + 1
    if target_idx < 0 or target_idx >= len(all_blogs):
        # Already at top or bottom boundary
        return {"success": True, "message": "Already at boundary", "sequence": curr_seq}

    target_blog = all_blogs[target_idx]
    target_seq = target_blog.get("sequence", 1)

    # If sequences are accidentally identical, adjust target
    if target_seq == curr_seq:
        target_seq = curr_seq - 1 if direction == "up" else curr_seq + 1

    # Swap in database
    db.blogs.update_one({"_id": current_blog["_id"]}, {"$set": {"sequence": target_seq}})
    db.blogs.update_one({"_id": target_blog["_id"]}, {"$set": {"sequence": curr_seq}})

    return {
        "success": True,
        "message": f"Moved {direction} successfully",
        "swapped": {
            "current_id": str(current_blog["_id"]),
            "new_sequence": target_seq,
            "target_id": str(target_blog["_id"]),
            "target_sequence": curr_seq
        }
    }
