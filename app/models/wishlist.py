from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Union
from app.models.common import PyObjectId

class WishlistItem(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_email: str
    product_id: Optional[str] = None
    product_title: str
    product_price: Union[str, float, int]
    product_image: Optional[str] = None
    product_slug: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True)
