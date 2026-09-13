from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.common import PyObjectId

class Blog(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    title: str
    slug: str
    category: str = "Design & Inspiration"
    author: str = "De Luzex Team"
    read_time: str = "5 min read"
    excerpt: Optional[str] = None
    content: str
    image: str
    is_featured: bool = False
    status: str = "Published"  # "Published" | "Draft"
    sequence: int = 1  # Integer sequence for ordering (1 = top, 2 = second, etc.)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
