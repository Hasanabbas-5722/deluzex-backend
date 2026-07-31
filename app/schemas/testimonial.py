from pydantic import BaseModel
from typing import Optional

class TestimonialBase(BaseModel):
    author_name: str
    author_title: Optional[str] = None
    text: str
    rating: float = 5.0
    avatar_url: Optional[str] = None

class TestimonialCreate(TestimonialBase):
    pass

class Testimonial(TestimonialBase):
    id: int

    class Config:
        from_attributes = True
