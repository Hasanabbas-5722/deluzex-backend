from pydantic import BaseModel, Field
from typing import Optional, Union, List, Dict, Any
from app.models.common import PyObjectId

class Product(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    product_title: str
    product_price: Optional[Union[float, int, str]] = 0

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

    # Design & Technical Specifications
    sku: Optional[str] = None
    stock_status: Optional[str] = "IN STOCK"
    in_stock: Optional[bool] = True
    price_prefix: Optional[str] = "From"
    price_note: Optional[str] = "per piece (volume contract applicable)"
    dimensions: Optional[str] = None
    finish: Optional[str] = None
    material: Optional[str] = None
    colorway: Optional[str] = None
    piece_weight: Optional[str] = None
    care: Optional[str] = None
    moq_rule: Optional[str] = None
    replenishment: Optional[str] = None
    whatsapp_number: Optional[str] = None
    phone_number: Optional[str] = None
    specifications: Optional[list[dict]] = []
    technical_spec_pdf: Optional[str] = None

    class Config:
        populate_by_name = True

