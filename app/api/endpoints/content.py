from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Body, status
from typing import Dict, Any, List, Optional
from datetime import datetime
from app import models
from app.api.deps import get_current_active_admin
from app.services.imagekit import upload_image_to_imagekit
from app.core.database import db

router = APIRouter()

DEFAULT_CONTENT: Dict[str, Dict[str, Any]] = {
    "homepage": {
        "hero": {
            "tagline": "Celebrate Every Moment with",
            "title": "Where Lights become Art",
            "description": "Crafted With Exceptional Materials And Refined Details To Elevate Modern Living Spaces.",
            "bg_image": "/images/hero_bg.png",
            "btn_explore_text": "Explore Collection",
            "btn_explore_link": "/shop",
            "btn_catalogue_text": "View Catalogue",
            "btn_catalogue_link": "/categories"
        },
        "statement": {
            "highlight_text": "Discover lighting crafted with precision and elegance, blending timeless design,",
            "sub_text": "exceptional quality, and warm illumination to transform every space."
        },
        "story": {
            "subtitle": "OUR STORY",
            "title": "A Passion For Light. A Commitment To Excellence.",
            "description": "De Luzex Was Born Out Of A Shared Passion For Transformative Design. We Believe That Light Is More Than Just A Functional Element; It Is A Medium For Artistic Expression.\n\nEvery Chandelier, Wall Light, And Pendant We Create Is Handcrafted With Precision By Master Artisans Who Share Our Vision For Bringing Elegance And Brilliance Into Every Space.",
            "image": "/images/about_chandelier_1784107790569.jpg",
            "stats": [
                {"number": "10+", "label": "Years Of Excellence", "image": "/images/project_lounge_1784107767735.jpg"},
                {"number": "98%", "label": "Client Satisfaction", "image": "/images/about_chandelier_1784107790569.jpg"},
                {"number": "500+", "label": "Lighting Installations", "image": "/images/project_lobby_1784107778993.jpg"},
                {"number": "50K+", "label": "Happy Customers", "image": "/images/project_lounge_1784107767735.jpg"}
            ]
        },
        "cta": {
            "title": "Discover Timeless Lighting",
            "description": "Elevate Your Interiors With Premium Lighting Collections Crafted To Bring Warmth, Elegance, And Sophistication To Every Space.",
            "btn_primary_text": "Shop Lighting",
            "btn_primary_link": "/shop",
            "btn_secondary_text": "Learn more",
            "btn_secondary_link": "/about"
        }
    },
    "about": {
        "hero": {
            "title": "Crafting Light For\nExtraordinary Interiors",
            "description": "We Create Timeless Lighting Pieces That Blend Artistry, Craftsmanship, And Innovation To Elevate Every Space.",
            "bg_image": "/images/project_lobby_1784107778993.jpg",
            "btn_text": "Explore Portfolio",
            "btn_link": "/projects"
        },
        "story": {
            "subtitle": "OUR STORY",
            "title": "A Passion For Light.\nA Commitment To Excellence.",
            "description": "De Luzex Was Born Out Of A Shared Passion For Transformative Design. We Believe That Light Is More Than Just A Functional Element; It Is A Medium For Artistic Expression.\n\nEvery Chandelier, Wall Light, And Pendant We Create Is Handcrafted With Precision By Master Artisans Who Share Our Vision For Bringing Elegance And Brilliance Into Every Space.",
            "image": "/images/project_lounge_1784107767735.jpg",
            "features": [
                {"icon": "bespoke", "title": "Bespoke Design"},
                {"icon": "star", "title": "Unrivaled Excellence"},
                {"icon": "layers", "title": "Luxury Finishes"}
            ]
        },
        "stats": [
            {"number": "10+", "label": "Years Of Excellence"},
            {"number": "98%", "label": "Client Satisfaction"},
            {"number": "500+", "label": "Lighting Installations"},
            {"number": "50K", "label": "Happy Customers"}
        ],
        "why_choose_us": {
            "subtitle": "WHY CHOOSE US",
            "title": "Why client Choose Us",
            "description": "Our belief is in a shared passion for transformative design. We see light as a medium for artistic expression, not just a functional element.",
            "image": "/images/about_chandelier_1784107790569.jpg",
            "items": [
                {"title": "Timeless Design Excellence", "description": "We blend traditional craftsmanship with contemporary aesthetics to create fixtures that remain elegant for years to come."},
                {"title": "Expert Artisanal Craftsmanship", "description": "Every piece is meticulously handcrafted by skilled artisans, ensuring unparalleled attention to detail and unmatched quality."},
                {"title": "Premium Materials", "description": "We source only the finest materials—from high-grade crystals to premium metals—to guarantee durability and a luxurious finish."},
                {"title": "Bespoke Lighting Solutions", "description": "From grand hotel lobbies to intimate dining rooms, we offer personalized designs tailored to perfectly complement your unique space."}
            ],
            "btn_text": "Book A Consultation",
            "btn_link": "/contact"
        },
        "cta": {
            "title": "Custom Lighting For\nEvery Project",
            "description": "We Create Custom Chandeliers And Unique Fixtures That Perfectly Match The Style Of Your Space.",
            "btn_primary_text": "Book A Consultation",
            "btn_primary_link": "/contact",
            "btn_secondary_text": "View Our Projects",
            "btn_secondary_link": "/projects"
        }
    },
    "site_settings": {
        "brand_name": "deluzex",
        "tagline": "Where Lights become Design",
        "logo_url": "/images/logo.png",
        "phone": "+1 (800) 456-7890",
        "email": "concierge@deluzex.com",
        "address": "450 Luxury Avenue, Suite 1200, Mayfair, London",
        "working_hours": "Mon - Fri: 9:00 AM - 7:00 PM GMT",
        "social_links": {
            "instagram": "https://instagram.com",
            "facebook": "https://facebook.com",
            "linkedin": "https://linkedin.com",
            "twitter": "https://twitter.com"
        },
        "footer_copyright": "© 2026 Deluzex Luxury Lighting. All rights reserved."
    }
}

def seed_defaults_if_missing():
    """Ensure all default content documents exist in MongoDB."""
    for key, default_data in DEFAULT_CONTENT.items():
        doc = db.site_content.find_one({"key": key})
        if not doc:
            db.site_content.insert_one({
                "key": key,
                "data": default_data,
                "updated_at": datetime.utcnow()
            })

@router.get("", response_model=List[models.SiteContent])
def read_all_content():
    """Fetch all site content sections, auto-seeding defaults if empty."""
    seed_defaults_if_missing()
    docs = list(db.site_content.find())
    return [models.SiteContent(**doc) for doc in docs]

@router.get("/{key}", response_model=models.SiteContent)
def get_content_by_key(key: str):
    """Fetch a specific content block by key (e.g. 'homepage', 'about', 'site_settings')."""
    seed_defaults_if_missing()
    doc = db.site_content.find_one({"key": key})
    if not doc:
        # If unknown key but in defaults, insert and return
        if key in DEFAULT_CONTENT:
            new_item = {
                "key": key,
                "data": DEFAULT_CONTENT[key],
                "updated_at": datetime.utcnow()
            }
            res = db.site_content.insert_one(new_item)
            new_item["_id"] = res.inserted_id
            return models.SiteContent(**new_item)
        raise HTTPException(status_code=404, detail=f"Content block '{key}' not found")

    return models.SiteContent(**doc)

@router.put("/{key}", response_model=models.SiteContent)
def update_content_by_key(
    key: str,
    payload: Dict[str, Any] = Body(...),
    current_user: models.User = Depends(get_current_active_admin),
):
    """
    Update or create content by key (Admin only).
    Merges updated data and persists to MongoDB.
    """
    seed_defaults_if_missing()
    now = datetime.utcnow()

    existing = db.site_content.find_one({"key": key})
    if existing:
        # Merge or replace data payload
        updated_data = payload.get("data", payload)
        db.site_content.update_one(
            {"key": key},
            {"$set": {"data": updated_data, "updated_at": now}}
        )
        existing["data"] = updated_data
        existing["updated_at"] = now
        return models.SiteContent(**existing)
    else:
        new_doc = {
            "key": key,
            "data": payload.get("data", payload),
            "updated_at": now
        }
        res = db.site_content.insert_one(new_doc)
        new_doc["_id"] = res.inserted_id
        return models.SiteContent(**new_doc)

@router.post("/upload-image")
async def upload_cms_image(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_active_admin),
):
    """
    Direct image uploader to ImageKit for CMS sections.
    """
    try:
        url = await upload_image_to_imagekit(file, folder="/cms")
        return {"success": True, "url": url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")
