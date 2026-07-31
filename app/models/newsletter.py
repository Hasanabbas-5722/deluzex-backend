from beanie import Document
from pydantic import EmailStr, Field
from datetime import datetime

class NewsletterSubscriber(Document):
    email: EmailStr
    subscribed_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "newsletter_subscribers"
