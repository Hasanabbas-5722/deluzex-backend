from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.common import PyObjectId

class HeroProduct(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    image: str
    name: str
    price: float
    alt: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
