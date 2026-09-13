from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Any, Dict
from app.models.common import PyObjectId

class AuditLog(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: Optional[PyObjectId] = None
    actor_email: Optional[str] = None
    actor_name: Optional[str] = None
    actor_role: str = "User"  # "Admin", "Customer", "System"
    action: str               # "ADMIN_LOGIN", "USER_LOGIN", "PRODUCT_CREATE", etc.
    action_category: str = "general" # "auth", "catalog", "orders", "cms", "security"
    target_type: Optional[str] = None # "product", "category", "order", "auth", "cms"
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    description: Optional[str] = None
    details: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str = "SUCCESS"    # "SUCCESS", "FAILED", "WARNING"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True)

