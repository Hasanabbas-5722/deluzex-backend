from beanie import Document
from typing import Optional

class Testimonial(Document):
    author_name: str
    author_title: Optional[str] = None
    text: str
    rating: float = 5.0
    avatar_url: Optional[str] = None

    class Settings:
        name = "testimonials"
