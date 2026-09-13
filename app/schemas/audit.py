from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from datetime import datetime

class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    actor_email: Optional[str] = None
    actor_name: Optional[str] = None
    actor_role: str = "User"
    action: str
    action_category: str = "general"
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    description: Optional[str] = None
    details: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str = "SUCCESS"
    created_at: datetime

class ActionBreakdown(BaseModel):
    category: str
    count: int = 0

class AuditStatsResponse(BaseModel):
    total_events: int
    total_logins: int
    total_modifications: int
    total_unique_actors: int
    recent_24h_events: int
    category_counts: Dict[str, int]
