from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class NewsletterSubscriberBase(BaseModel):
    email: EmailStr

class NewsletterSubscriberCreate(NewsletterSubscriberBase):
    pass

class NewsletterSubscriber(NewsletterSubscriberBase):
    id: int
    subscribed_at: datetime

    class Config:
        from_attributes = True
