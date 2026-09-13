from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from app.models.common import PyObjectId

class Category(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    category_id: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)
