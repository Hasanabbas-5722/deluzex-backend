from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from app.models.common import PyObjectId

class VisitorLog(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    visitor_id: str
    session_id: str
    path: str
    referrer: Optional[str] = ""
    ip_address: Optional[str] = ""
    user_agent: Optional[str] = ""
    device_type: str = "Desktop"  # "Desktop", "Mobile", "Tablet"
    browser: str = "Other"        # "Chrome", "Safari", "Edge", "Firefox", etc.
    os: str = "Other"             # "macOS", "iOS", "Windows", "Android", "Linux"
    is_member: bool = False
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True)
