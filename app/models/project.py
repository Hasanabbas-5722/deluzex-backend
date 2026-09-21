from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.common import PyObjectId

class Project(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    title: str
    location: Optional[str] = None
    category: Optional[str] = "Residential"
    subtitle: Optional[str] = None
    description: Optional[str] = None
    installations_count: Optional[str] = None
    image_url: Optional[str] = None
    gallery_images: List[str] = []
    videos: List[str] = []
    is_featured: bool = False
    sequence: int = 1
    year: Optional[str] = None
    scope: Optional[str] = None
    area: Optional[str] = None
    client: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
