from beanie import Document, PydanticObjectId
from typing import Optional

class Product(Document):
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

    class Settings:
        name = "products"
