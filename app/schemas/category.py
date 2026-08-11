from pydantic import BaseModel
from typing import Optional

class CategoryBase(BaseModel):
    name: str
    category_id: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: str

    class Config:
        from_attributes = True

