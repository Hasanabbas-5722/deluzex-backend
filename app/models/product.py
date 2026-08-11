from pydantic import BaseModel, Field
from typing import Optional
from app.models.common import PyObjectId

class Product(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    product_title: str
    product_price: int
    product_description: Optional[str] = None
    product_category: Optional[str] = None
    product_material: Optional[str] = None
    product_voltage: Optional[str] = None
    product_style: Optional[str] = None
    product_finishing: Optional[str] = None
    stock_count: int = 0
    is_featured: bool = False
    is_new_arrival: bool = False
    product_main_image: Optional[str] = None
    product_images: list[str] = []

    class Config:
        populate_by_name = True
