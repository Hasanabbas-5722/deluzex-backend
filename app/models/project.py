from beanie import Document
from typing import Optional

class Project(Document):
    title: str
    subtitle: Optional[str] = None
    installations_count: Optional[str] = None
    image_url: Optional[str] = None
    is_featured: bool = False

    class Settings:
        name = "projects"
