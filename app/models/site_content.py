from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.common import PyObjectId

class SiteContent(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    key: str  # e.g., 'homepage', 'about', 'site_settings'
    data: Dict[str, Any] = {}
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
