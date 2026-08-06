from pydantic import BaseModel, Field
from typing import Optional
from app.models.common import PyObjectId

class Project(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    title: str
    subtitle: Optional[str] = None
    installations_count: Optional[str] = None
    image_url: Optional[str] = None
    is_featured: bool = False

    class Config:
        populate_by_name = True
