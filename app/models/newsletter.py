from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from app.models.common import PyObjectId

class NewsletterSubscriber(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    email: EmailStr
    subscribed_at: datetime = Field(default_factory=datetime.utcnow)
    is_notified: bool = Field(default=False)
    notified_at: Optional[datetime] = None
    source: Optional[str] = "coming_soon"

    class Config:
        populate_by_name = True
