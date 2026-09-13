from pydantic import BaseModel, ConfigDict
from typing import Optional, Union
from datetime import datetime

class WishlistItemBase(BaseModel):
    user_email: str
    product_id: Optional[str] = None
    product_title: str
    product_price: Union[str, float, int]
    product_image: Optional[str] = None
    product_slug: Optional[str] = None

class WishlistItemCreate(WishlistItemBase):
    pass

class WishlistItemResponse(WishlistItemBase):
    id: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
