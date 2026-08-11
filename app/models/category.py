from pydantic import BaseModel, Field
from typing import Optional
from app.models.common import PyObjectId

class Category(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    category_id: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        populate_by_name = True
