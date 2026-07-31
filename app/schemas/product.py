from pydantic import BaseModel
from typing import Optional
from .category import Category

class ProductBase(BaseModel):
    title: str
    price: float
    description: Optional[str] = None
    category_id: Optional[int] = None
    stock_count: int = 0
    rating: float = 0.0
    review_count: int = 0
    image_url: Optional[str] = None
    is_featured: bool = False
    is_new_arrival: bool = False

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    category: Optional[Category] = None

    class Config:
        from_attributes = True
