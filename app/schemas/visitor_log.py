from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class VisitEventCreate(BaseModel):
    visitor_id: str
    session_id: str
    path: str
    referrer: Optional[str] = ""
    user_agent: Optional[str] = ""
    screen_width: Optional[int] = None
    is_member: bool = False
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    user_id: Optional[str] = None

class VisitorLogResponse(BaseModel):
    id: str
    visitor_id: str
    session_id: str
    path: str
    referrer: Optional[str] = ""
    ip_address: Optional[str] = ""
    device_type: str = "Desktop"
    browser: str = "Other"
    os: str = "Other"
    is_member: bool = False
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class DeviceBreakdown(BaseModel):
    desktop: int = 0
    mobile: int = 0
    tablet: int = 0

class TopPage(BaseModel):
    path: str
    views: int

class DailyTrend(BaseModel):
    date: str
    total_views: int
    unique_visitors: int
    member_views: int

class AnalyticsStatsResponse(BaseModel):
    total_page_views: int = 0
    total_unique_visitors: int = 0
    total_member_visitors: int = 0
    total_guest_visitors: int = 0
    active_now: int = 0
    devices: DeviceBreakdown
    top_pages: List[TopPage] = []
    daily_trends: List[DailyTrend] = []

class MemberActivity(BaseModel):
    email: str
    name: str
    total_visits: int
    last_seen: datetime
    last_path: str
