from pydantic import BaseModel
from typing import Optional

class ProjectBase(BaseModel):
    title: str
    subtitle: Optional[str] = None
    installations_count: Optional[str] = None
    image_url: Optional[str] = None
    is_featured: bool = False

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int

    class Config:
        from_attributes = True
