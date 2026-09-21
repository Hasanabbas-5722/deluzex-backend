from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.common import PyObjectId

class Review(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    product_id: str
    author_name: str
    author_email: Optional[str] = None
    rating: int = Field(default=5, ge=1, le=5)
    title: Optional[str] = None
    text: str
    created_at: Optional[datetime] = None

    class Config:
        populate_by_name = True

class ReviewCreate(BaseModel):
    product_id: str
    author_name: str
    author_email: Optional[str] = None
    rating: int = Field(default=5, ge=1, le=5)
    title: Optional[str] = None
    text: str
