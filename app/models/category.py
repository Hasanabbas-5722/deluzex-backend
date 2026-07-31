from beanie import Document
from typing import Optional

class Category(Document):
    name: str
    category_id: Optional[str] = None
    image_url: Optional[str] = None

    class Settings:
        name = "categories"
