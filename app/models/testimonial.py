from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.common import PyObjectId

class Testimonial(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    author_name: str
    author_title: Optional[str] = None
    text: str
    rating: float = 5.0
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
